import sys
import os
import time
import asyncio
import sqlite3
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine_v2.golden_dataset_generator_v2.orchestrator_v2 import GoldenDatasetOrchestratorV2
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH

logging.basicConfig(level=logging.WARNING)

async def test_long_emails():
    print("="*90)
    print("🧪 ENGINE V2 OPTION A TEST ON REAL MEDIUM & LONG EMAILS (150 - 600 WORDS)")
    print("="*90)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, size_category, word_count, clean_text, raw_text 
        FROM raw_emails 
        WHERE size_category IN ('medium', 'long') AND status='backtranslated' 
        ORDER BY word_count DESC 
        LIMIT 5
    """)
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("❌ Error: No medium/long backtranslated records found.")
        return

    orch_v2 = GoldenDatasetOrchestratorV2()

    for idx, (e_id, cat, words, c_text, r_text) in enumerate(rows):
        text = c_text if (c_text and len(c_text.strip('- \n\t')) >= 10) else r_text
        text = text[:4000]

        t0 = time.time()
        human_email = orch_v2._step_01_ingest(text, str(e_id))
        persona_v2 = await orch_v2._step_02_extract_persona(human_email)
        dpbc = orch_v2._step_03_get_dpbc_thresholds(persona_v2, human_email)

        champion = await orch_v2.run_pipeline_v2(
            email_id=e_id,
            original_email_text=text,
            persona=persona_v2,
            dpbc=dpbc
        )
        elapsed = time.time() - t0

        print(f"\n📩 EMAIL {idx+1} [Record ID: {e_id} | Category: {cat.upper()} | Word Count: {words} words]")
        print(f"   Raw Text Snippet (First 200 chars):\n   \"{text[:200]}...\"")
        print(f"\n   Persona NLP Task : {persona_v2.nlp_task} | Formality: {persona_v2.formality_scale}")
        print(f"   Generated Super Prompt (Engine v2 Option A):\n   👉 {champion.final_prompt_text}")
        print(f"   Performance      : Time = {elapsed:.2f}s | Error Delta (Δ) = {champion.elo_delta:.4f}")
        print("-" * 90)

if __name__ == "__main__":
    asyncio.run(test_long_emails())
