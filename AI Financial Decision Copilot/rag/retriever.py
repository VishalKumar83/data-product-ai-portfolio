"""
rag/retriever.py
─────────────────
HybridRetriever — merges FAISS (dense) and ChromaDB (dense + metadata filtering)
results using Reciprocal Rank Fusion (RRF) for robust retrieval.

Usage:
    retriever = HybridRetriever()
    docs = retriever.retrieve("What was Apple's revenue in 2023?", top_k=5)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
import faiss
import numpy as np
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent))
import config
from rag.embeddings import EmbeddingModel


@dataclass
class RetrievedDocument:
    id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)
    source: str = "unknown"   # "faiss" | "chroma" | "hybrid"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata,
            "source": self.source,
        }


class FAISSRetriever:
    """Dense retriever backed by a persisted FAISS flat-L2 index."""

    def __init__(self, embedder: EmbeddingModel):
        self.embedder = embedder
        self._index: faiss.Index | None = None
        self._metadata: dict[str, dict] = {}
        self._load()

    def _load(self):
        index_path = Path(config.FAISS_INDEX_PATH)
        index_file = index_path / "index.bin"
        meta_file = index_path / "metadata.json"

        if not index_file.exists():
            logger.warning(f"FAISS index not found at {index_file}. Run ingestion first.")
            return

        self._index = faiss.read_index(str(index_file))
        self._metadata = json.loads(meta_file.read_text())
        logger.info(f"FAISS index loaded: {self._index.ntotal} vectors, dim={self._index.d}")

    def retrieve(self, query: str, top_k: int = 10,
                 filter_ticker: str | None = None) -> list[RetrievedDocument]:
        if self._index is None or self._index.ntotal == 0:
            return []

        q_emb = self.embedder.encode(query).reshape(1, -1)
        distances, indices = self._index.search(q_emb, top_k * 2)  # over-fetch for filtering

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            meta = self._metadata.get(str(idx), {})
            if filter_ticker and meta.get("ticker", "").upper() != filter_ticker.upper():
                continue
            results.append(RetrievedDocument(
                id=meta.get("id", str(idx)),
                text=meta.get("text", ""),
                score=float(1 / (1 + dist)),   # convert L2 distance → similarity score
                metadata={k: v for k, v in meta.items() if k not in ("id", "text")},
                source="faiss",
            ))
            if len(results) >= top_k:
                break

        return results


class ChromaRetriever:
    """Dense retriever backed by a persistent ChromaDB collection."""

    def __init__(self, embedder: EmbeddingModel):
        self.embedder = embedder
        self._collection = None
        self._load()

    def _load(self):
        try:
            client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
            self._collection = client.get_collection(config.CHROMA_COLLECTION_NAME)
            logger.info(f"ChromaDB collection loaded: {self._collection.count()} docs")
        except Exception as e:
            logger.warning(f"ChromaDB not available: {e}. Run ingestion first.")

    def retrieve(self, query: str, top_k: int = 10,
                 filter_ticker: str | None = None) -> list[RetrievedDocument]:
        if self._collection is None:
            return []

        q_emb = self.embedder.encode(query).tolist()
        where = {"ticker": filter_ticker.upper()} if filter_ticker else None

        try:
            result = self._collection.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return []

        docs = []
        for doc, meta, dist in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            docs.append(RetrievedDocument(
                id=result["ids"][0][len(docs)],
                text=doc,
                score=float(1 - dist),   # cosine distance → similarity
                metadata=meta,
                source="chroma",
            ))
        return docs


class HybridRetriever:
    """
    Merges FAISS and ChromaDB results via Reciprocal Rank Fusion (RRF).
    RRF score = Σ 1/(k + rank_i) where k=60 is a smoothing constant.
    """

    RRF_K = 60

    def __init__(self):
        logger.info("Initializing HybridRetriever...")
        self.embedder = EmbeddingModel()
        self.faiss_retriever = FAISSRetriever(self.embedder)
        self.chroma_retriever = ChromaRetriever(self.embedder)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_ticker: str | None = None,
        strategy: str | None = None,
    ) -> list[RetrievedDocument]:
        """
        Retrieve top-k documents for a query.

        Args:
            query: Natural language question or statement
            top_k: Number of results (default: config.TOP_K_RETRIEVAL)
            filter_ticker: Optional ticker symbol to restrict results
            strategy: 'faiss' | 'chroma' | 'hybrid' (default: config.RETRIEVAL_STRATEGY)
        """
        top_k = top_k or config.TOP_K_RETRIEVAL
        strategy = strategy or config.RETRIEVAL_STRATEGY

        if strategy == "faiss":
            return self.faiss_retriever.retrieve(query, top_k, filter_ticker)
        if strategy == "chroma":
            return self.chroma_retriever.retrieve(query, top_k, filter_ticker)

        # Hybrid: run both and fuse
        faiss_results = self.faiss_retriever.retrieve(query, top_k * 2, filter_ticker)
        chroma_results = self.chroma_retriever.retrieve(query, top_k * 2, filter_ticker)
        return self._rrf_merge(faiss_results, chroma_results, top_k)

    def _rrf_merge(
        self,
        list_a: list[RetrievedDocument],
        list_b: list[RetrievedDocument],
        top_k: int,
    ) -> list[RetrievedDocument]:
        """Reciprocal Rank Fusion of two ranked lists."""
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, RetrievedDocument] = {}

        for rank, doc in enumerate(list_a):
            rrf_scores[doc.id] = rrf_scores.get(doc.id, 0) + 1 / (self.RRF_K + rank + 1)
            doc_map[doc.id] = doc

        for rank, doc in enumerate(list_b):
            rrf_scores[doc.id] = rrf_scores.get(doc.id, 0) + 1 / (self.RRF_K + rank + 1)
            if doc.id not in doc_map:
                doc_map[doc.id] = doc

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        merged = []
        for doc_id, score in ranked[:top_k]:
            doc = doc_map[doc_id]
            doc.score = score
            doc.source = "hybrid"
            merged.append(doc)

        return merged

    def format_context(self, docs: list[RetrievedDocument]) -> str:
        """Format retrieved docs into a prompt context block."""
        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            header = f"[{i}] {meta.get('ticker', 'N/A')} | {meta.get('filing_date', 'N/A')} | {meta.get('section', 'N/A')}"
            parts.append(f"{header}\n{doc.text}")
        return "\n\n---\n\n".join(parts)
