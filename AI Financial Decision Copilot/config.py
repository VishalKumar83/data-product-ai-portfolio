"""
config.py - Centralized configuration management
Loads all settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", DATA_DIR / "raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", DATA_DIR / "processed"))
FILINGS_DIR = Path(os.getenv("FILINGS_DIR", RAW_DATA_DIR / "sec_filings"))
MODELS_DIR = BASE_DIR / "models"
EVAL_DIR = BASE_DIR / "evaluation"

# Ensure directories exist
for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, FILINGS_DIR, MODELS_DIR, EVAL_DIR / "results"]:
    d.mkdir(parents=True, exist_ok=True)

# ── Ollama / LLM ───────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3:8b")
OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
AGENT_TEMPERATURE: float = float(os.getenv("AGENT_TEMPERATURE", "0.1"))

# ── Fine-tuned model ───────────────────────────────────────────────────────────
FINETUNED_MODEL_PATH: str = os.getenv("FINETUNED_MODEL_PATH", str(MODELS_DIR / "llama3-financial-lora"))
USE_FINETUNED_MODEL: bool = os.getenv("USE_FINETUNED_MODEL", "false").lower() == "true"

# ── Vector Stores ──────────────────────────────────────────────────────────────
FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", str(PROCESSED_DATA_DIR / "faiss_index"))
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(PROCESSED_DATA_DIR / "chroma_db"))
CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "sec_10k_filings")

# ── RAG Config ─────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "64"))
TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "5"))
RETRIEVAL_STRATEGY: str = os.getenv("RETRIEVAL_STRATEGY", "hybrid")  # faiss | chroma | hybrid

# ── Agent Config ───────────────────────────────────────────────────────────────
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
VERBOSE_AGENTS: bool = os.getenv("VERBOSE_AGENTS", "true").lower() == "true"

# ── API ────────────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"

# ── Observability ──────────────────────────────────────────────────────────────
ENABLE_OBSERVABILITY: bool = os.getenv("ENABLE_OBSERVABILITY", "false").lower() == "true"
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# ── Evaluation ─────────────────────────────────────────────────────────────────
EVAL_DATASET_PATH: str = os.getenv("EVAL_DATASET_PATH", str(EVAL_DIR / "qa_benchmark.json"))
RAGAS_OUTPUT_PATH: str = os.getenv("RAGAS_OUTPUT_PATH", str(EVAL_DIR / "results"))
