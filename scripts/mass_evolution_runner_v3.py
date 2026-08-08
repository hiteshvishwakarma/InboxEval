import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

from tqdm.asyncio import tqdm
from src.engine_v3.golden_dataset_generator_v3.orchestrator_v3 import GoldenDatasetOrchestratorV3
from src.engine_v3.golden_dataset_generator_v3.diversity_sampler import DiversitySampler
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH
import json

try:
    import aiosqlite
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiosqlite"])
    import aiosqlite

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("MassEvolutionRunnerV3")

CONCURRENCY_LIMIT = 20

async def process_email_v3(orchestrator_v3, row, semaphore, db):
    email_id = row['id']
    raw_text = row['raw_text']
    
    # Parse the JSON payloads from the database directly!
    try:
        from src.engine_v3.golden_dataset_generator_v3.schemas import PersonaProfileV3
        from src.engine.golden_dataset_generator.schemas import DPBCThresholds
        persona_v3 = PersonaProfileV3(**json.loads(row['target_persona']))
        dpbc = DPBCThresholds(**json.loads(row['dpbc_targets']))
    except Exception as e:
        logger.error(f"Failed to parse DB JSON for {email_id}: {e}")
        return

    async with semaphore:
        try:
            # Step 04-12 Engine v3 Pipeline (Vertical only)
            golden_record = await orchestrator_v3.run_pipeline_v3(
                email_id=email_id,
                original_email_text=raw_text,
                persona=persona_v3,
                dpbc=dpbc
            )

            # Step 12: Export Golden Record into SQLite database
            await db.execute(
                """INSERT INTO golden_dataset 
                   (raw_email_id, original_text, synthetic_text, target_persona, kda_winner_mutation_id, tone_score, conciseness_score, accuracy_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email_id,
                    raw_text,
                    golden_record.final_prompt_text if hasattr(golden_record, 'final_prompt_text') else str(golden_record),
                    persona_v3.typology_classification,
                    golden_record.id if hasattr(golden_record, 'id') else "mut_v3_winner",
                    dpbc.tone_target,
                    dpbc.conciseness_target,
                    dpbc.accuracy_target
                )
            )

            await db.execute("UPDATE raw_emails SET status='completed' WHERE id=?", (email_id,))
            await db.commit()
            
        except Exception as e:
            logger.error(f"Engine v3 failed to evolve record {email_id}: {e}")
            await db.execute("UPDATE raw_emails SET status='failed', error_log=? WHERE id=?", (str(e), email_id))
            await db.commit()

async def main():
    print("🚀 Initializing Engine v3 Mass Evolution Runner (Smart Feedback Loop)")
    orchestrator_v3 = GoldenDatasetOrchestratorV3()
    sampler = DiversitySampler(DB_PATH)
    
    BATCH_SIZE = 100
    pending_rows = []
    
    print(f"Sampling {BATCH_SIZE} raw emails using the Smart Diversity Sampler...")
    for _ in range(BATCH_SIZE):
        row = sampler.get_next_best_email()
        if row:
            pending_rows.append(row)
        else:
            break
            
    if not pending_rows:
        print("All records processed or none available in 'backtranslated' state.")
        return

    print(f"Engine v3 evolving {len(pending_rows)} emails concurrently with {CONCURRENCY_LIMIT} workers...")
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async with aiosqlite.connect(DB_PATH) as db:
        
        tasks = []
        for row in pending_rows:
            tasks.append(asyncio.create_task(process_email_v3(orchestrator_v3, row, semaphore, db)))
            
        await tqdm.gather(*tasks, desc="Engine v3 Mass Evolution", unit="email")
        
    print("\n🎯 Engine v3 Mass Evolution Complete!")

if __name__ == "__main__":
    asyncio.run(main())
