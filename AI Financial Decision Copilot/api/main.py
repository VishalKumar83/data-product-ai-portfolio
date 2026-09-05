"""
api/main.py
────────────
FastAPI application — REST endpoints for the Financial RAG system.

Endpoints:
  POST /query          → Run a financial question through the full crew pipeline
  POST /retrieve       → Retrieve raw document chunks without agent reasoning
  GET  /health         → Health check (Ollama, FAISS, ChromaDB)
  GET  /filings        → List indexed SEC filings
  POST /batch          → Run multiple queries
  GET  /docs           → Auto-generated Swagger UI
"""

import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

import config
from agents.financial_crew import FinancialAnalysisCrew
from rag.retriever import HybridRetriever

# ── App state ──────────────────────────────────────────────────────────────────
_crew: FinancialAnalysisCrew | None = None
_retriever: HybridRetriever | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize heavy objects once on startup."""
    global _crew, _retriever
    logger.info("Starting Agentic Financial RAG API...")
    _retriever = HybridRetriever()
    _crew = FinancialAnalysisCrew()
    logger.success("API ready.")
    yield
    logger.info("Shutting down API...")


app = FastAPI(
    title="Agentic Financial RAG System",
    description=(
        "Multi-agent RAG pipeline over SEC 10-K filings. "
        "Powered by CrewAI + LLaMA-3 (Ollama) + FAISS + ChromaDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, description="Financial question")
    ticker: str | None = Field(None, description="Optional stock ticker filter e.g. AAPL")
    verbose: bool = Field(False, description="Enable verbose agent logging")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What was Apple's total revenue in fiscal year 2023?",
                "ticker": "AAPL",
            }
        }
    }


class QueryResponse(BaseModel):
    query: str
    final_answer: str
    ticker: str | None
    elapsed_seconds: float
    error: str | None
    metadata: dict


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Search query")
    ticker: str | None = Field(None, description="Optional ticker filter")
    top_k: int = Field(5, ge=1, le=20)
    strategy: str = Field("hybrid", description="faiss | chroma | hybrid")


class BatchQueryRequest(BaseModel):
    queries: list[QueryRequest] = Field(..., max_length=10)


class HealthResponse(BaseModel):
    status: str
    ollama: str
    faiss: str
    chromadb: str
    model: str
    timestamp: float


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check connectivity to Ollama, FAISS, and ChromaDB."""
    import json
    from pathlib import Path

    # Check Ollama
    ollama_status = "❌ unavailable"
    try:
        import ollama
        client = ollama.Client(host=config.OLLAMA_BASE_URL)
        client.list()
        ollama_status = f"✅ connected ({config.OLLAMA_MODEL})"
    except Exception as e:
        ollama_status = f"❌ {e}"

    # Check FAISS
    faiss_status = "❌ not indexed"
    faiss_path = Path(config.FAISS_INDEX_PATH) / "index.bin"
    if faiss_path.exists():
        try:
            import faiss
            idx = faiss.read_index(str(faiss_path))
            faiss_status = f"✅ {idx.ntotal} vectors"
        except Exception as e:
            faiss_status = f"❌ {e}"

    # Check ChromaDB
    chroma_status = "❌ not indexed"
    try:
        import chromadb
        client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        col = client.get_collection(config.CHROMA_COLLECTION_NAME)
        chroma_status = f"✅ {col.count()} docs"
    except Exception as e:
        chroma_status = f"❌ not indexed"

    overall = "healthy" if "✅" in ollama_status else "degraded"
    return HealthResponse(
        status=overall,
        ollama=ollama_status,
        faiss=faiss_status,
        chromadb=chroma_status,
        model=config.OLLAMA_MODEL,
        timestamp=time.time(),
    )


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def run_query(request: QueryRequest):
    """
    Run a financial question through the full multi-agent pipeline.
    Retriever → Analyst → Validator agents work sequentially.
    """
    if _crew is None:
        raise HTTPException(status_code=503, detail="Crew not initialized")

    result = _crew.run(
        query=request.query,
        ticker=request.ticker,
        verbose=request.verbose,
    )

    return QueryResponse(**result.to_dict())


@app.post("/retrieve", tags=["Retrieval"])
async def retrieve_documents(request: RetrieveRequest):
    """
    Retrieve raw document chunks from the vector store without agent reasoning.
    Useful for debugging retrieval quality.
    """
    if _retriever is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

    docs = _retriever.retrieve(
        query=request.query,
        top_k=request.top_k,
        filter_ticker=request.ticker,
        strategy=request.strategy,
    )

    return {
        "query": request.query,
        "num_results": len(docs),
        "strategy": request.strategy,
        "documents": [d.to_dict() for d in docs],
    }


@app.post("/batch", tags=["Query"])
async def run_batch(request: BatchQueryRequest, background_tasks: BackgroundTasks):
    """Run multiple queries sequentially. Max 10 queries per request."""
    if _crew is None:
        raise HTTPException(status_code=503, detail="Crew not initialized")

    results = []
    for q in request.queries:
        result = _crew.run(query=q.query, ticker=q.ticker)
        results.append(result.to_dict())

    return {"results": results, "count": len(results)}


@app.get("/filings", tags=["System"])
async def list_filings():
    """List all SEC filings currently indexed in the knowledge base."""
    import json
    from pathlib import Path

    meta_file = Path(config.FAISS_INDEX_PATH) / "metadata.json"
    if not meta_file.exists():
        return {"indexed": False, "message": "Run ingestion first: python scripts/ingest_documents.py"}

    meta = json.loads(meta_file.read_text())
    from collections import defaultdict
    filing_map = defaultdict(list)
    for v in meta.values():
        filing_map[v.get("ticker", "?")].append(v.get("filing_date", "?"))

    summary = {ticker: sorted(set(dates)) for ticker, dates in filing_map.items()}
    return {
        "indexed": True,
        "total_chunks": len(meta),
        "filings": summary,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "name": "Agentic Financial RAG System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_RELOAD,
        log_level=config.API_LOG_LEVEL if hasattr(config, "API_LOG_LEVEL") else "info",
    )
