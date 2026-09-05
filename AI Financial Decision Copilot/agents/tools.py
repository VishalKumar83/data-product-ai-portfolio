"""
agents/tools.py
────────────────
Custom CrewAI tools used by the Retriever, Analyst, and Validator agents.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from crewai_tools import BaseTool
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).parent.parent))
from rag.retriever import HybridRetriever

# Singleton retriever (shared across tools to avoid reloading indexes)
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


# ── Tool Input Schemas ────────────────────────────────────────────────────────

class RetrieveInput(BaseModel):
    query: str = Field(..., description="Natural language question to retrieve context for")
    ticker: Optional[str] = Field(None, description="Optional: filter by stock ticker e.g. AAPL")
    top_k: Optional[int] = Field(5, description="Number of documents to retrieve (default 5)")
    strategy: Optional[str] = Field("hybrid", description="Retrieval strategy: faiss | chroma | hybrid")


class ValidateInput(BaseModel):
    claim: str = Field(..., description="The financial claim or statement to fact-check")
    context: str = Field(..., description="The source context to validate the claim against")


class CalculateInput(BaseModel):
    expression: str = Field(..., description="A Python arithmetic expression to evaluate (e.g. '(150 - 120) / 120 * 100')")


# ── Tools ─────────────────────────────────────────────────────────────────────

class FinancialRetrievalTool(BaseTool):
    name: str = "financial_retrieval"
    description: str = (
        "Retrieves relevant passages from SEC 10-K filings using hybrid vector search "
        "(FAISS + ChromaDB). Use this to find financial data, risk factors, MD&A sections, "
        "revenue figures, and other filing content. Accepts an optional ticker filter."
    )
    args_schema: type[BaseModel] = RetrieveInput

    def _run(self, query: str, ticker: str | None = None,
             top_k: int = 5, strategy: str = "hybrid") -> str:
        retriever = get_retriever()
        docs = retriever.retrieve(query, top_k=top_k, filter_ticker=ticker, strategy=strategy)

        if not docs:
            return "No relevant documents found. The indexes may not be built yet."

        context = retriever.format_context(docs)
        summary = f"Retrieved {len(docs)} document chunks.\n\n{context}"
        return summary


class FactValidationTool(BaseTool):
    name: str = "fact_validation"
    description: str = (
        "Validates whether a financial claim is supported by the provided source context. "
        "Returns SUPPORTED, CONTRADICTED, or INSUFFICIENT_EVIDENCE with a brief explanation."
    )
    args_schema: type[BaseModel] = ValidateInput

    def _run(self, claim: str, context: str) -> str:
        from rag.llm import OllamaLLM
        llm = OllamaLLM()
        prompt = f"""You are a financial fact-checker. Determine if the following claim is supported by the context.

CLAIM: {claim}

CONTEXT:
{context}

Respond with one of:
- SUPPORTED: <brief reason>
- CONTRADICTED: <brief reason>
- INSUFFICIENT_EVIDENCE: <brief reason>

Be concise and precise. Only use the provided context."""
        return llm.complete(prompt)


class FinancialCalculatorTool(BaseTool):
    name: str = "financial_calculator"
    description: str = (
        "Evaluates safe arithmetic expressions for financial calculations. "
        "Use for percentages, growth rates, ratios, etc. "
        "Example: '(150_000 - 120_000) / 120_000 * 100' for YoY growth %"
    )
    args_schema: type[BaseModel] = CalculateInput

    # Allowed names in eval context
    _SAFE_GLOBALS = {"__builtins__": {}, "abs": abs, "round": round, "min": min, "max": max}

    def _run(self, expression: str) -> str:
        try:
            # Strip underscores used as numeric separators
            clean_expr = expression.replace("_", "").replace(",", "")
            result = eval(clean_expr, self._SAFE_GLOBALS, {})  # noqa: S307
            return f"Result: {result:.4f}"
        except Exception as e:
            return f"Calculation error: {e}. Check the expression format."


class SECFilingMetadataTool(BaseTool):
    name: str = "sec_filing_metadata"
    description: str = (
        "Lists available SEC 10-K filings in the knowledge base, "
        "showing which tickers and years are indexed."
    )

    def _run(self) -> str:
        import json
        from pathlib import Path
        import config

        meta_file = Path(config.FAISS_INDEX_PATH) / "metadata.json"
        if not meta_file.exists():
            return "No indexed filings found. Run ingestion first."

        meta = json.loads(meta_file.read_text())
        tickers = sorted({v.get("ticker", "?") for v in meta.values()})
        dates = sorted({v.get("filing_date", "?") for v in meta.values()})
        return (
            f"Indexed filings:\n"
            f"  Tickers: {', '.join(tickers)}\n"
            f"  Filing dates: {', '.join(dates[:10])}{'...' if len(dates) > 10 else ''}\n"
            f"  Total chunks: {len(meta)}"
        )
