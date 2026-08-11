import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

from tqdm.asyncio import tqdm
from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH
from src.engine.golden_dataset_generator.schemas import PersonaProfile, DPBCThresholds

try:
    import aiosqlite
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiosqlite"])
    import aiosqlite

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("MassEvolutionRunner")

CONCURRENCY_LIMIT = 60

async def process_email(orchestrator, row, semaphore, db):
    email_id = row[0]
    clean_text = row[1]
    prompt = row[2]
    email_id, clean_text, p_text, ctx, target_persona = row
    
    async with semaphore:
        try:
            # Step 01: Ingest HumanEmail object
            human_email = orchestrator._step_01_ingest(clean_text, str(email_id))

            # Step 02: Extract PersonaProfile
            target_persona_obj = await orchestrator._step_02_extract_persona(human_email)

            # Step 03: DPBC Thresholds
            dpbc = orchestrator._step_03_get_dpbc_thresholds(target_persona_obj, human_email)

            # Steps 04-12: Full Evolutionary FSM Loop
            golden_record = await orchestrator.run_pipeline(
                email_id=email_id,
                original_email_text=clean_text,
                persona=target_persona_obj,
                dpbc=dpbc
            )

            # Step 12: Export Golden Record into SQLite database table
            await db.execute(
                """INSERT INTO golden_dataset 
                   (raw_email_id, original_text, synthetic_text, target_persona, kda_winner_mutation_id, tone_score, conciseness_score, accuracy_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email_id,
                    clean_text,
                    golden_record.final_prompt_text if hasattr(golden_record, 'final_prompt_text') else str(golden_record),
                    target_persona_obj.typology_classification,
                    golden_record.id if hasattr(golden_record, 'id') else "mut_winner",
                    dpbc.tone_target,
                    dpbc.conciseness_target,
                    dpbc.accuracy_target
                )
            )

            # Mark email as completed in raw_emails table
            await db.execute("UPDATE raw_emails SET status='completed' WHERE id=?", (email_id,))
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to evolve record {email_id}: {e}")
            await db.execute("UPDATE raw_emails SET status='failed', error_log=? WHERE id=?", (str(e), email_id))
            await db.commit()

async def main():
    print("🚀 Initializing Mass Evolution Runner (Steps 4-12) via true Asyncio")
    orchestrator = GoldenDatasetOrchestrator()
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, clean_text, raw_text, prompt, context, target_persona FROM raw_emails WHERE status='backtranslated' AND id NOT IN (SELECT raw_email_id FROM golden_dataset)") as cursor:
            pending_rows = await cursor.fetchall()
            
        if not pending_rows:
            print("All records processed or none available in 'backtranslated' state.")
            return
            
        # Clean up text fallbacks for rows where clean_text was just dashes & enforce max length safety
        cleaned_pending_rows = []
        for row in pending_rows:
            r_id, c_text, r_text, p_text, ctx, persona = row
            text_to_use = c_text if (c_text and len(c_text.strip('- \n\t')) >= 10) else r_text
            if text_to_use:
                text_to_use = text_to_use[:8000] # Safe 8000 character cap to prevent vLLM >4096 context errors
            cleaned_pending_rows.append((r_id, text_to_use, p_text, ctx, persona))

        print(f"Evolving {len(cleaned_pending_rows)} emails concurrently...")
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        
        tasks = []
        for row in cleaned_pending_rows:
            tasks.append(asyncio.create_task(process_email(orchestrator, row, semaphore, db)))
            
        await tqdm.gather(*tasks, desc="Evolving Golden Dataset", unit="email")
        
    print("\n🎯 Mass Evolution Complete!")

if __name__ == "__main__":
    asyncio.run(main())
