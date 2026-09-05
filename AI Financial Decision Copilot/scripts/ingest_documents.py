"""
scripts/ingest_documents.py
────────────────────────────
Processes raw SEC 10-K filings into chunked documents,
then builds both FAISS and ChromaDB vector stores.

Pipeline:
  Raw .txt/.htm files → Clean text → Hybrid chunks → FAISS + ChromaDB indexes

Usage:
    python scripts/ingest_documents.py
    python scripts/ingest_documents.py --rebuild   # force rebuild indexes
"""

import json
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import chromadb
import faiss
import numpy as np
from loguru import logger
from tqdm import tqdm

import config
from rag.embeddings import EmbeddingModel

# ── Text cleaning ──────────────────────────────────────────────────────────────

HTML_TAG_RE = re.compile(r"<[^>]+>")
MULTI_SPACE_RE = re.compile(r"\s{3,}")
XBRL_RE = re.compile(r"<ix:[^>]+>.*?</ix:[^>]+>", re.DOTALL)
EXHIBIT_RE = re.compile(r"EXHIBIT\s+\d+[\.\d]*", re.IGNORECASE)


def clean_filing_text(raw: str) -> str:
    """Strip HTML/XBRL markup and normalize whitespace from SEC filings."""
    # Remove XBRL inline tags
    text = XBRL_RE.sub("", raw)
    # Remove HTML tags
    text = HTML_TAG_RE.sub(" ", text)
    # Decode common HTML entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&") \
               .replace("&lt;", "<").replace("&gt;", ">") \
               .replace("&#160;", " ").replace("&quot;", '"')
    # Normalize whitespace
    text = MULTI_SPACE_RE.sub("\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text


# ── Section-aware chunking ─────────────────────────────────────────────────────

SECTION_HEADERS = [
    r"ITEM\s+1[A-Z]?\.",   # Item 1, 1A, 1B…
    r"ITEM\s+2\.",
    r"ITEM\s+3\.",
    r"ITEM\s+4\.",
    r"ITEM\s+5\.",
    r"ITEM\s+6\.",
    r"ITEM\s+7[A-Z]?\.",
    r"ITEM\s+8\.",
    r"ITEM\s+9[A-Z]?\.",
    r"PART\s+[IVX]+",
]
SECTION_RE = re.compile("|".join(SECTION_HEADERS), re.IGNORECASE)


def split_into_sections(text: str) -> list[tuple[str, str]]:
    """
    Split filing into (section_title, section_text) pairs.
    Falls back to sliding-window chunking if no sections found.
    """
    matches = list(SECTION_RE.finditer(text))
    if len(matches) < 2:
        return [("FULL_DOCUMENT", text)]

    sections = []
    for i, match in enumerate(matches):
        title = match.group(0).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((title, text[start:end]))
    return sections


def chunk_text(text: str, chunk_size: int = config.CHUNK_SIZE,
               overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    """Sliding-window token-approximate chunking by word count."""
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        if len(chunk.strip()) > 50:  # skip tiny chunks
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def process_filing(filepath: Path) -> list[dict]:
    """
    Parse a single SEC filing into a list of chunk dicts:
    {id, text, metadata: {ticker, date, section, source}}
    """
    raw = filepath.read_text(encoding="utf-8", errors="replace")
    text = clean_filing_text(raw)

    # Extract metadata from filename: AAPL_2023-11-03_10K.txt
    parts = filepath.stem.split("_")
    ticker = parts[0] if parts else "UNKNOWN"
    date = parts[1] if len(parts) > 1 else "unknown"

    sections = split_into_sections(text)
    chunks = []
    chunk_id = 0
    for section_title, section_text in sections:
        for chunk in chunk_text(section_text):
            chunks.append({
                "id": f"{ticker}_{date}_{chunk_id:04d}",
                "text": chunk,
                "metadata": {
                    "ticker": ticker,
                    "filing_date": date,
                    "section": section_title,
                    "source_file": filepath.name,
                    "chunk_index": chunk_id,
                },
            })
            chunk_id += 1
    return chunks


# ── Index building ─────────────────────────────────────────────────────────────

def build_faiss_index(chunks: list[dict], embedder: "EmbeddingModel") -> None:
    """Encode all chunks and persist a FAISS flat-L2 index + metadata JSON."""
    logger.info(f"Building FAISS index over {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode_batch(texts, batch_size=64, show_progress=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    # Wrap in IDMap for direct id lookup
    id_index = faiss.IndexIDMap(index)
    ids = np.arange(len(chunks), dtype=np.int64)
    id_index.add_with_ids(embeddings, ids)

    # Save index
    index_path = Path(config.FAISS_INDEX_PATH)
    index_path.mkdir(parents=True, exist_ok=True)
    faiss.write_index(id_index, str(index_path / "index.bin"))

    # Save metadata mapping
    meta = {str(i): chunks[i]["metadata"] | {"text": chunks[i]["text"], "id": chunks[i]["id"]}
            for i in range(len(chunks))}
    (index_path / "metadata.json").write_text(json.dumps(meta, indent=2))
    logger.success(f"FAISS index saved → {index_path}/index.bin  (dim={dim}, n={len(chunks)})")


def build_chroma_index(chunks: list[dict], embedder: "EmbeddingModel") -> None:
    """Add all chunks to a ChromaDB persistent collection."""
    logger.info(f"Building ChromaDB index over {len(chunks)} chunks...")
    client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)

    # Delete existing collection if rebuilding
    try:
        client.delete_collection(config.CHROMA_COLLECTION_NAME)
        logger.info("Dropped existing ChromaDB collection.")
    except Exception:
        pass

    collection = client.create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Batch upsert in groups of 500
    batch_size = 500
    for start in tqdm(range(0, len(chunks), batch_size), desc="ChromaDB upsert"):
        batch = chunks[start: start + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = embedder.encode_batch(texts, batch_size=64)
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=texts,
            embeddings=[e.tolist() for e in embeddings],
            metadatas=[c["metadata"] for c in batch],
        )

    logger.success(f"ChromaDB index saved → {config.CHROMA_PERSIST_DIR}  ({collection.count()} docs)")


def main(rebuild: bool = False):
    filings_dir = Path(config.FILINGS_DIR)
    filing_files = list(filings_dir.rglob("*_10K.txt"))

    if not filing_files:
        logger.error(
            f"No 10-K .txt files found in {filings_dir}.\n"
            "Run: python scripts/download_sec_filings.py first."
        )
        sys.exit(1)

    logger.info(f"Found {len(filing_files)} filing files.")

    # Check if indexes already exist
    faiss_exists = (Path(config.FAISS_INDEX_PATH) / "index.bin").exists()
    chroma_exists = (Path(config.CHROMA_PERSIST_DIR) / "chroma.sqlite3").exists()
    if faiss_exists and chroma_exists and not rebuild:
        logger.info("Indexes already exist. Use --rebuild to force recreation.")
        return

    # Process all filings
    all_chunks: list[dict] = []
    for fp in tqdm(filing_files, desc="Processing filings"):
        chunks = process_filing(fp)
        all_chunks.extend(chunks)
        logger.info(f"  {fp.name}: {len(chunks)} chunks")

    logger.info(f"Total chunks: {len(all_chunks)}")

    # Save processed chunks manifest
    manifest_path = Path(config.PROCESSED_DATA_DIR) / "chunks_manifest.json"
    manifest_path.write_text(json.dumps(all_chunks[:100], indent=2))  # sample
    logger.info(f"Chunk manifest sample saved → {manifest_path}")

    # Build embedder
    from rag.embeddings import EmbeddingModel
    embedder = EmbeddingModel()

    # Build both indexes
    build_faiss_index(all_chunks, embedder)
    build_chroma_index(all_chunks, embedder)
    logger.success("Ingestion complete. You can now start the API.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of existing indexes")
    args = parser.parse_args()
    main(rebuild=args.rebuild)
