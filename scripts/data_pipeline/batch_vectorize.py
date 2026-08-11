"""
Step 02b: Batch vectorization into Chroma (inbox_eval_vectors).

SQLite: READ ONLY (SELECT clean_text / target_persona). Never UPDATE/INSERT.
Chroma: WRITE via collection.upsert under exclusive chroma_write_lock.

Usage:
  python3 scripts/data_pipeline/batch_vectorize.py --batch-id <id>
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import chromadb
import sentence_transformers
import sqlite3

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
_PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _PIPELINE)

from chroma_lock import chroma_write_lock
from diversity_batch import ensure_diversity_batch_table, get_batch_ids

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BatchVectorize")

DB_PATH = os.path.abspath(os.path.join(_ROOT, "data/pipeline.db"))
CHROMA_DIR = os.path.abspath(os.path.join(_ROOT, "data/chroma_db"))
BATCH_SIZE = 256


def fetch_rows(conn: sqlite3.Connection, batch_id: str | None) -> list:
    """
    Read-only fetch. Prefer claimed batch IDs; no status='backtranslated' required
    so Step 02b can run in parallel with Step 01.
    """
    if batch_id:
        ensure_diversity_batch_table(conn)
        ids = get_batch_ids(conn, batch_id)
        if not ids:
            logger.warning("No IDs in diversity_batch for batch_id=%s", batch_id)
            return []
        placeholders = ",".join("?" * len(ids))
        cursor = conn.execute(
            f"SELECT id, clean_text, target_persona FROM raw_emails WHERE id IN ({placeholders})",
            ids,
        )
        return cursor.fetchall()

    cursor = conn.execute(
        "SELECT id, clean_text, target_persona FROM raw_emails WHERE status='backtranslated'"
    )
    return cursor.fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 02b: Chroma batch vectorize")
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Only vectorize IDs in this diversity_batch (recommended)",
    )
    parser.add_argument(
        "--lock-timeout",
        type=float,
        default=1800,
        help="Seconds to wait for Chroma write lock (default 1800)",
    )
    args = parser.parse_args()

    logger.info("Starting Batch Vectorization (Step 02b / KNN Vector Storage)")
    logger.info("Database Path: %s", DB_PATH)
    logger.info("ChromaDB Storage Directory: %s", CHROMA_DIR)

    if not os.path.exists(DB_PATH):
        logger.error("Database file not found at %s", DB_PATH)
        sys.exit(1)

    # SQLite read-only snapshot — close before Chroma work.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=30)
    try:
        rows = fetch_rows(conn, args.batch_id)
    finally:
        conn.close()

    total_emails = len(rows)
    logger.info("Found %s emails to vectorize (batch_id=%s).", total_emails, args.batch_id)
    if total_emails == 0:
        logger.warning("No emails found to vectorize.")
        return

    logger.info("Loading sentence-transformers model 'BAAI/bge-base-en-v1.5'...")
    model = sentence_transformers.SentenceTransformer("BAAI/bge-base-en-v1.5")

    with chroma_write_lock(
        timeout_sec=args.lock_timeout,
        chroma_dir=CHROMA_DIR,
        holder="batch_vectorize",
    ):
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        collection = chroma_client.get_or_create_collection(
            name="inbox_eval_vectors",
            metadata={"hnsw:space": "cosine"},
        )
        existing_count = collection.count()
        logger.info("ChromaDB collection currently contains %s vectorized records.", existing_count)

        # Skip IDs already present (idempotent re-runs).
        all_ids = [str(r[0]) for r in rows]
        already: set[str] = set()
        for i in range(0, len(all_ids), BATCH_SIZE):
            chunk = all_ids[i : i + BATCH_SIZE]
            got = collection.get(ids=chunk)
            already.update(got.get("ids") or [])

        to_write = [r for r in rows if str(r[0]) not in already]
        logger.info(
            "Skipping %s already-vectorized IDs; upserting %s new.",
            len(rows) - len(to_write),
            len(to_write),
        )

        for i in range(0, len(to_write), BATCH_SIZE):
            batch_rows = to_write[i : i + BATCH_SIZE]
            ids = [str(r[0]) for r in batch_rows]
            texts = [f"[{r[2] or 'Default Persona'}] {r[1]}" for r in batch_rows]
            metadatas = [
                {
                    "email_id": r[0],
                    "target_persona": (r[2] or "Default Persona")[:500],
                    "clean_text_snippet": (r[1] or "")[:200],
                }
                for r in batch_rows
            ]
            embeddings = model.encode(texts, show_progress_bar=False).tolist()
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts,
            )
            logger.info("Upserted batch %s–%s", i, i + len(batch_rows))

        final_count = collection.count()
        logger.info(
            "Batch Vectorization Complete! Total ChromaDB Vector Store Size: %s records.",
            final_count,
        )


if __name__ == "__main__":
    main()
