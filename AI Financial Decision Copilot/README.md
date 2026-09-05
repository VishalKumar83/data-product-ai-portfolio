# 📊 Agentic Financial RAG System

A production-grade **multi-agent Retrieval-Augmented Generation (RAG)** pipeline for querying and analyzing **SEC 10-K filings**. Built with **CrewAI**, **LLaMA-3** (via Ollama), **FAISS + ChromaDB hybrid retrieval**, and evaluated with **RAGAS**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI  (:8501)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────────┐
│                     FastAPI  (:8000)                            │
│              POST /query  │  POST /retrieve  │  GET /health     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    CrewAI Orchestrator                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Retriever   │→ │   Analyst    │→ │      Validator       │  │
│  │    Agent     │  │    Agent     │  │       Agent          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼───────────────────── ┼─────────────┘
          │                 │                       │
┌─────────▼─────────────────▼───────────────────── ▼─────────────┐
│                    RAG Layer                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Hybrid Retriever (RRF Fusion)                  │  │
│  │   ┌─────────────────┐    ┌─────────────────────────┐    │  │
│  │   │  FAISS (dense)  │    │  ChromaDB (dense+filter) │    │  │
│  │   └─────────────────┘    └─────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │    Embedding Model: Ollama nomic-embed-text (local)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│                Ollama  (:11434)  LLaMA-3 8B                  │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Pipeline

| Agent | Role | Tools |
|---|---|---|
| **RetrieverAgent** | Searches 10-K knowledge base with optimized queries | `financial_retrieval`, `sec_filing_metadata` |
| **AnalystAgent** | Synthesizes data, computes ratios & trends | `financial_retrieval`, `financial_calculator` |
| **ValidatorAgent** | Fact-checks all claims against source documents | `fact_validation`, `financial_retrieval`, `financial_calculator` |

---

## ✨ Features

- **Multi-agent orchestration** via CrewAI (sequential Retriever → Analyst → Validator)
- **Hybrid retrieval** — FAISS + ChromaDB fused via Reciprocal Rank Fusion (RRF)
- **Section-aware chunking** — respects 10-K structure (Item 1, Item 7 MDA, Item 8 Financials…)
- **LLaMA-3 fine-tuning** — LoRA/QLoRA scripts for domain adaptation
- **RAGAS evaluation** — 50-question benchmark measuring faithfulness, relevancy, precision, recall
- **FastAPI REST API** — `/query`, `/retrieve`, `/batch`, `/health`, `/filings`
- **Streamlit UI** — Ask questions, debug retrieval, compare tickers side-by-side
- **Full Docker Compose stack** — one command to run everything
- **Langfuse observability** — optional LLM tracing and experiment tracking

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- 8GB+ RAM (16GB recommended for LLaMA-3 8B)
- Docker + Docker Compose (for containerized deployment)

### Option A — Local Setup

**1. Clone and install**
```bash
git clone https://github.com/Nithin/agentic-financial-rag.git
cd agentic-financial-rag
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Edit .env if needed (defaults work out of the box with local Ollama)
```

**3. Start Ollama and pull models**
```bash
ollama serve                      # starts Ollama server
ollama pull llama3:8b             # ~4.7GB — the LLM
ollama pull nomic-embed-text      # ~270MB — embedding model
```

**4. Download SEC 10-K filings**
```bash
# Downloads 10-K filings for top 10 S&P 500 companies (2022 & 2023)
python scripts/download_sec_filings.py

# Or specify your own tickers/years:
python scripts/download_sec_filings.py --tickers AAPL MSFT NVDA --years 2022 2023
```

**5. Build vector indexes**
```bash
python scripts/ingest_documents.py
# Builds both FAISS and ChromaDB indexes (takes ~5-10 minutes)
```

**6. Start the API**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**7. Start the UI** (new terminal)
```bash
streamlit run ui/app.py
```

Open **http://localhost:8501** 🎉

---

### Option B — Docker Compose (Recommended)

```bash
git clone https://github.com/Nithin/agentic-financial-rag.git
cd agentic-financial-rag
cp .env.example .env

# Build and start all services (Ollama + API + UI)
docker compose -f docker/docker-compose.yml up -d --build

# Wait for Ollama to pull models (~5 min first time)
docker compose -f docker/docker-compose.yml logs -f ollama-init

# Once models are ready, download and ingest data
docker compose -f docker/docker-compose.yml exec api \
    python scripts/download_sec_filings.py
docker compose -f docker/docker-compose.yml exec api \
    python scripts/ingest_documents.py
```

| Service | URL |
|---|---|
| Streamlit UI | http://localhost:8501 |
| FastAPI | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Ollama | http://localhost:11434 |

---

## 💬 Example Queries

```python
# Via Python
from agents.financial_crew import FinancialAnalysisCrew

crew = FinancialAnalysisCrew()

result = crew.run(
    "What was Apple's total revenue and gross margin in FY2023? "
    "How did it compare to FY2022?",
    ticker="AAPL"
)
print(result.final_answer)
```

```bash
# Via CLI
python agents/financial_crew.py "What are NVIDIA's main risk factors in 2023?" --ticker NVDA

# Via API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was Microsoft cloud revenue growth in FY2023?", "ticker": "MSFT"}'
```

---

## 📁 Project Structure

```
agentic-financial-rag/
├── agents/
│   ├── crew_agents.py        # Retriever, Analyst, Validator agent definitions
│   ├── crew_tasks.py         # Task definitions with expected outputs
│   ├── financial_crew.py     # Main orchestrator (FinancialAnalysisCrew)
│   └── tools.py              # Custom CrewAI tools (retrieval, calculator, validator)
├── rag/
│   ├── embeddings.py         # Ollama / sentence-transformer embedding wrapper
│   ├── retriever.py          # HybridRetriever: FAISS + ChromaDB + RRF fusion
│   └── llm.py                # OllamaLLM wrapper (streaming, retry, CrewAI compat)
├── api/
│   └── main.py               # FastAPI app (query, retrieve, batch, health endpoints)
├── ui/
│   └── app.py                # Streamlit frontend
├── scripts/
│   ├── download_sec_filings.py  # Downloads 10-Ks from SEC EDGAR (no API key needed)
│   ├── ingest_documents.py      # Builds FAISS + ChromaDB indexes
│   └── finetune_llama3.py       # LoRA/QLoRA fine-tuning on financial QA
├── evaluation/
│   ├── run_evaluation.py     # RAGAS evaluation pipeline + 50-Q benchmark
│   └── results/              # Evaluation output JSON files
├── docker/
│   ├── Dockerfile.api        # API service image
│   ├── Dockerfile.ui         # UI service image
│   └── docker-compose.yml    # Full stack compose file
├── data/
│   ├── raw/sec_filings/      # Downloaded 10-K .txt files (gitignored)
│   └── processed/            # FAISS index + ChromaDB (gitignored)
├── models/                   # Fine-tuned LoRA adapters (gitignored)
├── config.py                 # Centralized configuration (reads from .env)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔬 Fine-tuning LLaMA-3

Fine-tune the base LLaMA-3 model on financial Q&A for improved domain accuracy:

```bash
# QLoRA fine-tuning (recommended — works on 12GB GPU)
python scripts/finetune_llama3.py --qlora --epochs 3

# Full LoRA (requires 24GB+ VRAM)
python scripts/finetune_llama3.py --epochs 3

# Test fine-tuned model inference
python scripts/finetune_llama3.py --test \
    --test-question "What was Apple's gross margin in FY2023?"

# Enable fine-tuned model in .env:
# USE_FINETUNED_MODEL=true
```

**Fine-tuning details:**
- Base: `meta-llama/Meta-Llama-3-8B`
- Method: QLoRA (NF4 4-bit) + LoRA rank=16, alpha=32
- Target modules: all attention + MLP projection layers
- Dataset: 50+ financial Q&A pairs from SEC 10-K benchmark
- Optimizer: paged_adamw_32bit | LR scheduler: cosine with warmup

---

## 📈 Evaluation

Run the full RAGAS evaluation benchmark:

```bash
python evaluation/run_evaluation.py                   # all 50 questions
python evaluation/run_evaluation.py --questions 10    # quick test
python evaluation/run_evaluation.py --strategy faiss  # test single retriever
```

**RAGAS Metrics measured:**

| Metric | Description |
|---|---|
| **Faithfulness** | Are answers grounded in retrieved context? (no hallucination) |
| **Answer Relevancy** | Does the answer address the question? |
| **Context Precision** | Is retrieved context relevant to the question? |
| **Context Recall** | Does retrieved context contain all needed info? |

Results saved to `evaluation/results/eval_YYYYMMDD_HHMMSS.json` and viewable in the Streamlit Evaluation tab.

---

## ⚙️ Configuration

All settings are in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3:8b` | LLM model name |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `RETRIEVAL_STRATEGY` | `hybrid` | `faiss` / `chroma` / `hybrid` |
| `TOP_K_RETRIEVAL` | `5` | Documents retrieved per query |
| `CHUNK_SIZE` | `512` | Words per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap between chunks |
| `USE_FINETUNED_MODEL` | `false` | Use LoRA-adapted model |
| `ENABLE_OBSERVABILITY` | `false` | Enable Langfuse tracing |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **LLM** | LLaMA-3 8B via Ollama (local) |
| **Agent Framework** | CrewAI + LangChain |
| **Fine-tuning** | PEFT / LoRA / QLoRA (HuggingFace) |
| **Vector Store 1** | FAISS (dense retrieval) |
| **Vector Store 2** | ChromaDB (dense + metadata filtering) |
| **Embeddings** | nomic-embed-text (Ollama) / all-MiniLM-L6-v2 (fallback) |
| **Retrieval Fusion** | Reciprocal Rank Fusion (RRF) |
| **API** | FastAPI + Uvicorn |
| **UI** | Streamlit |
| **Evaluation** | RAGAS |
| **Observability** | Langfuse (optional) |
| **Containerization** | Docker + Docker Compose |
| **Data Source** | SEC EDGAR (public, no API key) |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built by [Nithin R](https://linkedin.com/in/nithin-r/) — Applied AI/ML Engineer*
