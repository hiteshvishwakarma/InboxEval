import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

from tqdm.asyncio import tqdm
from src.engine_v2.golden_dataset_generator_v2.orchestrator_v2 import GoldenDatasetOrchestratorV2
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH

try:
    import aiosqlite
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiosqlite"])
    import aiosqlite

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("MassEvolutionRunnerV2")

CONCURRENCY_LIMIT = 60

async def process_email_v2(orchestrator_v2, row, semaphore, db):
    email_id, clean_text, p_text, ctx, target_persona = row
    
    async with semaphore:
        try:
            # Step 01: Ingest HumanEmail object
            human_email = orchestrator_v2._step_01_ingest(clean_text, str(email_id))

            # Step 02: Extract PersonaProfileV2 AND pre-cache prompting strategies
            persona_v2 = await orchestrator_v2._step_02_extract_persona(human_email)

            # Step 03: DPBC Thresholds
            dpbc = orchestrator_v2._step_03_get_dpbc_thresholds(persona_v2, human_email)

            # Steps 04-12 Engine v2 Pipeline
            golden_record = await orchestrator_v2.run_pipeline_v2(
                email_id=email_id,
                original_email_text=clean_text,
                persona=persona_v2,
                dpbc=dpbc
            )

            # Step 12: Export Golden Record into SQLite database
            await db.execute(
                """INSERT INTO golden_dataset 
                   (raw_email_id, original_text, synthetic_text, target_persona, kda_winner_mutation_id, tone_score, conciseness_score, accuracy_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email_id,
                    clean_text,
                    golden_record.final_prompt_text if hasattr(golden_record, 'final_prompt_text') else str(golden_record),
                    persona_v2.typology_classification,
                    golden_record.id if hasattr(golden_record, 'id') else "mut_v2_winner",
                    dpbc.tone_target,
                    dpbc.conciseness_target,
                    dpbc.accuracy_target
                )
            )

            await db.execute("UPDATE raw_emails SET status='completed' WHERE id=?", (email_id,))
            await db.commit()
            
        except Exception as e:
            logger.error(f"Engine v2 failed to evolve record {email_id}: {e}")
            await db.execute("UPDATE raw_emails SET status='failed', error_log=? WHERE id=?", (str(e), email_id))
            await db.commit()

async def main():
    print("🚀 Initializing Engine v2 Mass Evolution Runner (Stratified Diversity Batch Sampling)")
    orchestrator_v2 = GoldenDatasetOrchestratorV2()
    
    from src.engine_v2.golden_dataset_generator_v2.diversity_sampler import fetch_stratified_diversity_batch
    
    pending_rows = fetch_stratified_diversity_batch(DB_PATH, batch_size=1000)
    if not pending_rows:
        print("All records processed or none available in 'backtranslated' state.")
        return
        
    cleaned_pending_rows = []
    for row in pending_rows:
        r_id, c_text, r_text, p_text, ctx, persona = row
        text_to_use = c_text if (c_text and len(c_text.strip('- \n\t')) >= 10) else r_text
        if text_to_use:
            text_to_use = text_to_use[:8000]
        cleaned_pending_rows.append((r_id, text_to_use, p_text, ctx, persona))

    print(f"Engine v2 evolving {len(cleaned_pending_rows)} emails concurrently with 60 workers (Stratified 20/20/20/20/20 Diversity Batch)...")
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with aiosqlite.connect(DB_PATH) as db:
        
        tasks = []
        for row in cleaned_pending_rows:
            tasks.append(asyncio.create_task(process_email_v2(orchestrator_v2, row, semaphore, db)))
            
        await tqdm.gather(*tasks, desc="Engine v2 Mass Evolution", unit="email")
        
    print("\n🎯 Engine v2 Mass Evolution Complete!")

if __name__ == "__main__":
    asyncio.run(main())
