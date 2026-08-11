"""
Step 02a: Horizontal enrichment — 11-axis persona + DPBC targets.

Keeps persona + DPBC as ONE step (single UPDATE). Waits on Chroma lock
(wait/retry) before opening Chroma for DPBC. Resumes rows with dpbc_targets IS NULL.

Usage:
  python3 scripts/mass_horizontal_enrichment.py --batch-id <id>
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sqlite3
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PIPELINE = os.path.join(_ROOT, "scripts", "data_pipeline")
sys.path.insert(0, _ROOT)
sys.path.insert(0, _PIPELINE)

from chroma_lock import chroma_write_lock
from diversity_batch import ensure_diversity_batch_table, get_batch_ids
from src.engine.golden_dataset_generator.engine_steps.step_03_vectorization import (
    get_dpbc_thresholds,
)
from src.engine.golden_dataset_generator.schemas import HumanEmail
from src.engine_v2.golden_dataset_generator_v2.schemas import PersonaProfileV3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MassHorizontalEnrichment")

DB_PATH = os.path.abspath(os.path.join(_ROOT, "data/pipeline.db"))


def setup_database_schema(db_path: str) -> None:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("ALTER TABLE raw_emails ADD COLUMN dpbc_targets TEXT;")
        logger.info("Added 'dpbc_targets' column to raw_emails.")
    except sqlite3.OperationalError:
        pass
    ensure_diversity_batch_table(conn)
    conn.commit()
    conn.close()


async def mock_extract_persona(raw_text: str) -> PersonaProfileV3:
    """Deterministic mock extractor for local testing without LLM calls."""
    return PersonaProfileV3(
        intent="Provide an update",
        sentiment="Neutral",
        nlp_task="Data Extraction",
        domain="General Corporate",
        format="Standard Email",
        power_dynamic="Peer to Peer",
        formality_scale="Professional",
        conciseness_tier="Standard",
        behavioral_quirks=["Direct", "Polite"],
        evidence_quotes=["Please see below"],
        prompting_strategies=[
            "The Executive (To the point)",
            "The Analyst (Detail oriented)",
            "The Lazy Minimalist",
            "The Micro-Manager",
            "The Storyteller",
        ],
        typology_classification="Corporate_Peer_DataExtraction",
    )


async def extract_persona_for_email(row, llm_client, test_mock, semaphore, model: str):
    async with semaphore:
        email_id = int(row["id"])
        clean_text = row["clean_text"]

        if test_mock:
            return email_id, await mock_extract_persona(clean_text)

        prompt = f"""
SYSTEM INSTRUCTIONS:
Analyze the provided email and extract a detailed Persona Profile (11 fields).

REQUIREMENTS:
1. 'nlp_task': MUST be EXACTLY ONE of: ['Zero-Shot Drafting', 'Data Extraction', 'Thread Summarization', 'Tone Translation'].
2. 'formality_scale': MUST be EXACTLY ONE of: ['Hyper-Casual', 'Casual', 'Semi-Professional', 'Professional', 'Hyper-Formal'].
3. 'conciseness_tier': MUST be EXACTLY ONE of: ['Hyper-Brief', 'Standard', 'Verbose', 'Rambling'].
4. 'prompting_strategies': Generate 5 diverse strategies this specific persona might use when typing into AI (e.g., 'The Lazy Minimalist', 'The Micro-Manager').

--- DYNAMIC INPUT DATA ---
Raw Email Text: {clean_text}
"""
        persona = None
        for attempt in range(3):
            try:
                persona = await llm_client.chat.completions.create(
                    model=model,
                    response_model=PersonaProfileV3,
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except Exception as e:
                if attempt == 2:
                    logger.error("Final failure for email %s: %s", email_id, e)
                else:
                    wait_time = 2**attempt
                    logger.warning(
                        "Extraction failed for email %s. Retrying in %ss...",
                        email_id,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
        return email_id, persona


def fetch_incomplete_rows(conn: sqlite3.Connection, batch_id: str | None, chunk_size: int):
    """Claimed (or any) rows still missing dpbc_targets. Pending OR backtranslated OK."""
    conn.row_factory = sqlite3.Row
    if batch_id:
        ensure_diversity_batch_table(conn)
        ids = get_batch_ids(conn, batch_id)
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        cursor = conn.execute(
            f"""
            SELECT id, raw_text, clean_text
            FROM raw_emails
            WHERE id IN ({placeholders})
              AND dpbc_targets IS NULL
            ORDER BY id
            """,
            ids,
        )
        return cursor.fetchall()

    cursor = conn.execute(
        """
        SELECT id, raw_text, clean_text
        FROM raw_emails
        WHERE dpbc_targets IS NULL
          AND size_category != 'micro'
          AND status IN ('pending', 'backtranslated')
        LIMIT ?
        """,
        (chunk_size,),
    )
    return cursor.fetchall()


async def run_enrichment(
    chunk_size: int,
    test_mock: bool,
    base_url: str,
    model: str,
    batch_id: str | None,
    lock_timeout: float,
) -> None:
    setup_database_schema(DB_PATH)

    if not test_mock:
        from openai import AsyncOpenAI
        import instructor

        llm_client = instructor.from_openai(
            AsyncOpenAI(api_key="mock-key", base_url=base_url)
        )
        logger.info("LLM client pointing at %s using model=%s", base_url, model)
    else:
        logger.info("Running in Mock Mode (No LLM API calls).")
        llm_client = None

    # Wait for Chroma lock BEFORE persona+DPBC so we never open Chroma while 02b writes.
    logger.info("Acquiring Chroma lock for Step 02a (wait/retry, no drop)...")
    with chroma_write_lock(
        timeout_sec=lock_timeout,
        holder="mass_horizontal_enrichment",
    ):
        total_processed = 0
        # Skip IDs that failed persona extraction this session to avoid infinite retry loops.
        skipped_ids: set[int] = set()
        while True:
            conn = sqlite3.connect(DB_PATH, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.row_factory = sqlite3.Row
            rows = fetch_incomplete_rows(conn, batch_id, chunk_size)
            rows = [r for r in rows if int(r["id"]) not in skipped_ids]

            if not rows:
                logger.info(
                    "No more incomplete emails. Total enriched this session: %s "
                    "(skipped failures: %s)",
                    total_processed,
                    len(skipped_ids),
                )
                conn.close()
                break

            logger.info(
                "Starting chunk of %s emails (batch_id=%s). Total so far: %s",
                len(rows),
                batch_id,
                total_processed,
            )

            semaphore = asyncio.Semaphore(5)
            tasks = [
                extract_persona_for_email(row, llm_client, test_mock, semaphore, model)
                for row in rows
            ]
            results = await asyncio.gather(*tasks)

            progressed = 0
            for row in rows:
                email_id = int(row["id"])
                raw_text = row["raw_text"]
                persona = next((p for eid, p in results if eid == email_id), None)
                if not persona:
                    skipped_ids.add(email_id)
                    logger.warning(
                        "Skipping email %s this session (persona extraction failed).",
                        email_id,
                    )
                    continue

                human_email_obj = HumanEmail(id=str(email_id), raw_text=raw_text)
                dpbc = get_dpbc_thresholds(persona, human_email_obj, None, None)

                # One UPDATE: persona + dpbc together (column ownership vs Step 01).
                conn.execute(
                    """
                    UPDATE raw_emails
                    SET target_persona = ?, dpbc_targets = ?
                    WHERE id = ? AND dpbc_targets IS NULL
                    """,
                    (persona.model_dump_json(), dpbc.model_dump_json(), email_id),
                )
                conn.commit()
                total_processed += 1
                progressed += 1
                logger.info("Email %s enriched (persona+dpbc).", email_id)

            conn.close()

            # batch_id mode: stop when a full pass made no progress (all remaining failed).
            if batch_id and progressed == 0:
                logger.warning(
                    "Batch %s: no progress on remaining incomplete rows; exiting. "
                    "Re-run later to retry skipped IDs.",
                    batch_id,
                )
                break
            # Non-batch continuous mode: if nothing progressed, avoid spin.
            if not batch_id and progressed == 0:
                logger.warning("No progress in chunk; exiting to avoid spin.")
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Step 02a: persona + DPBC enrichment")
    parser.add_argument("--batch-id", default=None, help="Scope to diversity_batch IDs")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=60,
        help="Max emails per fetch when not using --batch-id",
    )
    parser.add_argument("--test-mock", action="store_true", help="Mock LLM")
    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "OLLAMA_SECONDARY_LAPTOP_BASE_URL", "http://192.168.0.8:11434/v1"
        ),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_SECONDARY_LAPTOP_MODEL", "qwen2.5-coder:3b"),
    )
    parser.add_argument(
        "--lock-timeout",
        type=float,
        default=1800,
        help="Seconds to wait for Chroma lock (default 1800)",
    )
    args = parser.parse_args()

    asyncio.run(
        run_enrichment(
            args.chunk_size,
            args.test_mock,
            args.base_url,
            args.model,
            args.batch_id,
            args.lock_timeout,
        )
    )
