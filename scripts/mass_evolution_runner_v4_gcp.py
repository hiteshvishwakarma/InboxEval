import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

from tqdm.asyncio import tqdm
from src.engine_v4.golden_dataset_generator_v4.orchestrator_v4 import GoldenDatasetOrchestratorV4
from src.engine_v4.golden_dataset_generator_v4.diversity_sampler import DiversitySampler
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH
import json

try:
    import aiosqlite
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiosqlite"])
    import aiosqlite

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("MassEvolutionRunnerV4")

CONCURRENCY_LIMIT = 15

async def process_email_v4(orchestrator_v4, row, semaphore, db):
    email_id = row['id']
    raw_text = row['raw_text']
    
    # Parse the JSON payloads from the database directly!
    try:
        from src.engine_v4.golden_dataset_generator_v4.schemas import PersonaProfileV4
        from src.engine.golden_dataset_generator.schemas import DPBCThresholds
        persona_v4 = PersonaProfileV4(**json.loads(row['target_persona']))
        dpbc = DPBCThresholds(**json.loads(row['dpbc_targets']))
    except Exception as e:
        logger.error(f"Failed to parse DB JSON for {email_id}: {e}")
        return

    async with semaphore:
        try:
            # Step 04-12 Engine v3 Pipeline (Vertical only)
            golden_record = await orchestrator_v4.run_pipeline_v4(
                email_id=email_id,
                original_email_text=raw_text,
                persona=persona_v4,
                dpbc=dpbc
            )

            return (email_id, raw_text, golden_record, persona_v4, dpbc, "completed", None)
            
        except Exception as e:
            logger.error(f"Engine v4 failed to evolve record {email_id}: {e}")
            return (email_id, None, None, None, None, "failed", str(e))

async def main():
    print("🚀 Initializing Engine v4 Mass Evolution Runner (Smart Feedback Loop)")
    orchestrator_v4 = GoldenDatasetOrchestratorV4()
    sampler = DiversitySampler(DB_PATH)
    
    BATCH_SIZE = 100
    
    async with aiosqlite.connect(DB_PATH, timeout=60.0) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        while True:
            print(f"Sampling {BATCH_SIZE} raw emails using the Smart Diversity Sampler...")
            # Bug 5 & 7 Fix: Single batched DB hit on background thread
            pending_rows = await asyncio.to_thread(sampler.get_next_batch, BATCH_SIZE)
                    
            if not pending_rows:
                print("All records processed or none available in 'backtranslated' state.")
                break

            print(f"Engine v4 evolving {len(pending_rows)} emails concurrently with {CONCURRENCY_LIMIT} workers...")
            semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
            
            tasks = []
            for row in pending_rows:
                tasks.append(asyncio.create_task(process_email_v4(orchestrator_v4, row, semaphore, db)))
                
            results = await tqdm.gather(*tasks, desc="Engine v4 Mass Evolution Batch", unit="email")
            
            # Bug 6 Fix: Bulk commit at the batch level to eliminate write contention
            for res in results:
                email_id, raw_text, golden_record, persona_v4, dpbc, status, error_log = res
                if status == "completed":
                    await db.execute(
                        """INSERT INTO golden_dataset 
                           (raw_email_id, original_text, synthetic_text, target_persona, kda_winner_mutation_id, tone_score, conciseness_score, accuracy_score)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            email_id,
                            raw_text,
                            golden_record.final_prompt_text if hasattr(golden_record, 'final_prompt_text') else str(golden_record),
                            persona_v4.typology_classification,
                            golden_record.id if hasattr(golden_record, 'id') else "mut_v4_winner",
                            dpbc.tone_target,
                            dpbc.conciseness_target,
                            dpbc.accuracy_target
                        )
                    )
                    await db.execute("UPDATE raw_emails SET status='completed' WHERE id=?", (email_id,))
                else:
                    await db.execute("UPDATE raw_emails SET status='failed', error_log=? WHERE id=?", (error_log, email_id))
            
            await db.commit()
            
    print("\n🎯 Engine v4 Mass Evolution Complete!")

if __name__ == "__main__":
    asyncio.run(main())
