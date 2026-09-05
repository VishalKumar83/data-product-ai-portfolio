"""
rag/embeddings.py
──────────────────
Embedding model abstraction.
Primary: Ollama nomic-embed-text (local, free)
Fallback: sentence-transformers/all-MiniLM-L6-v2 (CPU, no API needed)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from loguru import logger
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
import config


class EmbeddingModel:
    """
    Wraps either Ollama embeddings or a local sentence-transformer.
    Auto-detects which backend is available.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or config.OLLAMA_EMBEDDING_MODEL
        self._backend: str = "ollama"
        self._st_model = None
        self._dim: int | None = None
        self._init()

    # ── Initialization ─────────────────────────────────────────────────────────

    def _init(self):
        """Try Ollama first; fall back to sentence-transformers."""
        if self._try_ollama():
            logger.info(f"Embedding backend: Ollama ({self.model_name})")
        else:
            logger.warning("Ollama not available — falling back to sentence-transformers")
            self._init_sentence_transformers()

    def _try_ollama(self) -> bool:
        try:
            import ollama
            test = ollama.embeddings(model=self.model_name, prompt="test")
            self._dim = len(test["embedding"])
            self._backend = "ollama"
            return True
        except Exception as e:
            logger.debug(f"Ollama unavailable: {e}")
            return False

    def _init_sentence_transformers(self):
        from sentence_transformers import SentenceTransformer
        self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
        self._dim = 384
        self._backend = "sentence_transformers"
        logger.info("Embedding backend: sentence-transformers (all-MiniLM-L6-v2, dim=384)")

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def dim(self) -> int:
        if self._dim is None:
            self.encode("warmup")
        return self._dim

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text string → 1-D numpy array."""
        return self.encode_batch([text])[0]

    def encode_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Encode a list of texts → 2-D numpy array (n, dim)."""
        if self._backend == "sentence_transformers":
            return self._encode_st(texts, batch_size, show_progress)
        return self._encode_ollama(texts, batch_size, show_progress)

    # ── Backends ───────────────────────────────────────────────────────────────

    def _encode_ollama(
        self, texts: list[str], batch_size: int, show_progress: bool
    ) -> np.ndarray:
        import ollama

        all_embeddings = []
        iterator = range(0, len(texts), batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Embedding (Ollama)")

        for i in iterator:
            batch = texts[i: i + batch_size]
            for text in batch:
                result = ollama.embeddings(model=self.model_name, prompt=text)
                all_embeddings.append(result["embedding"])

        arr = np.array(all_embeddings, dtype=np.float32)
        if self._dim is None:
            self._dim = arr.shape[1]
        return arr

    def _encode_st(
        self, texts: list[str], batch_size: int, show_progress: bool
    ) -> np.ndarray:
        embeddings = self._st_model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)
