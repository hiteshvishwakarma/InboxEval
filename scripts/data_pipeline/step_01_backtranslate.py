"""
Step 01: Stratified / batch-scoped backtranslation via DynamicGroqRotator
(llm_client_factory / GROQ_API_KEY* round-robin — not OmniRoute).

Writes ONLY: prompt, context, status='backtranslated'
Never writes target_persona (owned by Step 02a).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
_PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _PIPELINE)

from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH
from src.engine.golden_dataset_generator.utils.dynamic_groq_rotator import (
    CRITICAL_LLM_FAILURE,
    get_default_rotator,
)
from diversity_batch import (
    DEFAULT_BATCH_PER_CATEGORY,
    DEFAULT_CATEGORIES,
    claim_stratified_batch,
    ensure_diversity_batch_table,
)

try:
    import aiosqlite
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiosqlite"])
    import aiosqlite

load_dotenv(dotenv_path=os.path.join(_ROOT, ".env"))

CONCURRENCY_LIMIT = int(os.getenv("GROQ_CONCURRENCY", "5"))


async def backtranslate_email(email_text: str) -> dict | None:
    """Call Groq via DynamicGroqRotator; return JSON dict or None."""
    prompt = f"""You are an expert at reverse-engineering AI prompts.
Read the following real-world corporate email:
---
{email_text[:2000]}
---
Generate the 'Original Instruction' that a user would have typed into an AI assistant to generate this exact email.
Return ONLY a valid JSON object with exactly these keys (no extra text, no markdown):
{{
    "prompt": "<The instruction to generate the email>",
    "context": "<Any background facts or context needed to write it>",
    "target_persona": "<The persona of the sender>"
}}"""
    messages = [{"role": "user", "content": prompt}]
    try:
        rotator = get_default_rotator()
        data = await rotator.achat_completion(
            messages,
            temperature=0.3,
            response_format={"type": "json_object"},
            max_tokens=800,
            timeout=90.0,
        )
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content)
        model_used = data.get("_rotator_model", "?")
        print(f"   (model={model_used})")
        return parsed
    except CRITICAL_LLM_FAILURE as e:
        print(f"[!] GroqRotator exhausted: {e}")
        return None
    except Exception as e:
        print(f"[!] GroqRotator Error: {str(e)}")
        return None


async def process_email(row, semaphore, db, write_lock: asyncio.Lock) -> None:
    email_id = row[0]
    clean_text = row[1]

    async with semaphore:
        back_data = await backtranslate_email(clean_text)

        async with write_lock:
            if isinstance(back_data, dict):
                prompt_val = str(back_data.get("prompt", ""))
                context_val = str(back_data.get("context", ""))
                # Column ownership: never write target_persona (Step 02a owns it).
                # Allow retry from pending OR previously failed transport errors.
                cursor = await db.execute(
                    """
                    UPDATE raw_emails
                    SET prompt = ?, context = ?, status = 'backtranslated', error_log = NULL
                    WHERE id = ?
                      AND status IN ('pending', 'backtranslated', 'failed')
                      AND (prompt IS NULL OR prompt = '')
                    """,
                    (prompt_val, context_val, email_id),
                )
                await db.commit()
                if cursor.rowcount and cursor.rowcount > 0:
                    print(f"✅ Successfully backtranslated ID: {email_id}")
                else:
                    print(f"⚠️ No row updated for ID: {email_id} (already had prompt or bad status)")
            else:
                # Transport/API/parse failure: do NOT burn the row as permanent failed.
                # Leave status unchanged so the same batch_id can be re-run.
                await db.execute(
                    "UPDATE raw_emails SET error_log=? WHERE id=? AND (prompt IS NULL OR prompt='')",
                    ("Step01 transient failure (Groq/HTTP/JSON) — retry same batch", email_id),
                )
                await db.commit()
                print(f"⏳ Transient failure for ID: {email_id} — left retryable (not marked failed)")


async def main(batch_id: str | None, categories: list, batch_per_category: list) -> None:
    from src.engine.golden_dataset_generator.utils.dynamic_groq_rotator import (
        load_groq_api_keys,
        STEP_01_MODELS,
    )

    keys = load_groq_api_keys()
    print(
        f"🚀 Step 01: Backtranslation via DynamicGroqRotator "
        f"({len(keys)} Groq keys × {len(STEP_01_MODELS)} models)"
    )
    if not keys:
        print("ERROR: No GROQ_API_KEY / GROQ_API_KEY_* in environment (.env)")
        raise SystemExit(1)

    db_path = os.path.abspath(DB_PATH)
    async with aiosqlite.connect(db_path, timeout=30) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=30000")

        # Ensure claim table exists (sync helper via thread-safe execute of DDL)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS diversity_batch (
                batch_id TEXT NOT NULL,
                raw_email_id INTEGER PRIMARY KEY,
                size_category TEXT NOT NULL,
                claimed_at TEXT NOT NULL
            )
        """)
        await db.commit()

        if batch_id:
            async with db.execute(
                """
                SELECT r.id, r.clean_text
                FROM raw_emails r
                JOIN diversity_batch b ON b.raw_email_id = r.id
                WHERE b.batch_id = ?
                  AND (r.prompt IS NULL OR r.prompt = '')
                  AND r.status IN ('pending', 'backtranslated', 'failed')
                ORDER BY r.id
                """,
                (batch_id,),
            ) as cursor:
                pending_rows = await cursor.fetchall()
            print(f"Using existing BATCH_ID={batch_id}")
        else:
            # Claim new stratified batch using sync sqlite (same file, short transaction)
            import sqlite3

            sync_conn = sqlite3.connect(db_path, timeout=30)
            sync_conn.execute("PRAGMA busy_timeout=30000")
            ensure_diversity_batch_table(sync_conn)
            batch_id, claimed = claim_stratified_batch(
                sync_conn, categories=categories, batch_per_category=batch_per_category
            )
            sync_conn.close()
            print(f"Claimed new BATCH_ID={batch_id} ({len(claimed)} emails)")
            async with db.execute(
                """
                SELECT r.id, r.clean_text
                FROM raw_emails r
                JOIN diversity_batch b ON b.raw_email_id = r.id
                WHERE b.batch_id = ?
                  AND (r.prompt IS NULL OR r.prompt = '')
                  AND r.status IN ('pending', 'backtranslated', 'failed')
                ORDER BY r.id
                """,
                (batch_id,),
            ) as cursor:
                pending_rows = await cursor.fetchall()

        if not pending_rows:
            print("No emails needing backtranslation for this batch.")
            print(f"BATCH_ID={batch_id}")
            return

        print(f"Fetched {len(pending_rows)} emails. Concurrency={CONCURRENCY_LIMIT}...")
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        write_lock = asyncio.Lock()
        tasks = [
            asyncio.create_task(process_email(row, semaphore, db, write_lock))
            for row in pending_rows
        ]
        for i in range(0, len(tasks), 1000):
            await asyncio.gather(*tasks[i : i + 1000])

    print(f"🎯 Step 01 Session Complete! BATCH_ID={batch_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Step 01: Stratified Backtranslation via DynamicGroqRotator"
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Process claimed diversity_batch IDs (skip new claim)",
    )
    parser.add_argument(
        "--categories",
        default=",".join(DEFAULT_CATEGORIES),
        help="Used when claiming a new batch (default excludes micro)",
    )
    parser.add_argument(
        "--batch-per-category",
        default=",".join(str(n) for n in DEFAULT_BATCH_PER_CATEGORY),
        help="Per-category limits when claiming a new batch",
    )
    args = parser.parse_args()

    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    batches = [int(n.strip()) for n in args.batch_per_category.split(",")]
    if len(cats) != len(batches):
        print("ERROR: --categories and --batch-per-category must have the same number of items")
        raise SystemExit(1)

    asyncio.run(main(args.batch_id, cats, batches))
