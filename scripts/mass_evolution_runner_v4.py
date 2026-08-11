import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

from tqdm.asyncio import tqdm
from src.engine_v4.golden_dataset_generator_v4.orchestrator_v4 import GoldenDatasetOrchestratorV4
from src.engine_v4.golden_dataset_generator_v4.diversity_sampler import DiversitySampler
from src.engine_v4.golden_dataset_generator_v4.gpu_occupancy import (
    acquire_email_seat,
    configure,
    occupancy_snapshot,
    release_email_seat,
    DEFAULT_EMAIL_WORKERS,
)
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH
import json

try:
    import aiosqlite
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiosqlite"])
    import aiosqlite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MassEvolutionRunnerV4")

# Worker count ≈ email seats; actual admit is seat+metrics gated (see gpu_occupancy).
EMAIL_WORKERS = int(os.getenv("V4_EMAIL_WORKERS", str(DEFAULT_EMAIL_WORKERS)))


async def worker_task(worker_id, orchestrator_v4, task_queue, results_queue):
    while True:
        row = await task_queue.get()
        if row is None:
            task_queue.task_done()
            break

        email_id = row["id"]
        raw_text = row["raw_text"]
        size_category = row.get("size_category")
        seat_cost = 0

        try:
            from src.engine_v4.golden_dataset_generator_v4.schemas import PersonaProfileV4
            from src.engine.golden_dataset_generator.schemas import DPBCThresholds

            persona_v4 = PersonaProfileV4(**json.loads(row["target_persona"]))
            dpbc = DPBCThresholds(**json.loads(row["dpbc_targets"]))

            seat_cost = await acquire_email_seat(size_category)
            golden_record = await orchestrator_v4.run_pipeline_v4(
                email_id=email_id,
                original_email_text=raw_text,
                persona=persona_v4,
                dpbc=dpbc,
                size_category=size_category,
            )
            await results_queue.put(
                (email_id, raw_text, golden_record, persona_v4, dpbc, "completed", None)
            )
        except Exception as e:
            logger.error("Worker %s failed to evolve record %s: %s", worker_id, email_id, e)
            await results_queue.put((email_id, None, None, None, None, "failed", str(e)))
        finally:
            if seat_cost:
                await release_email_seat(seat_cost)
            task_queue.task_done()


async def consumer_task(results_queue, db_path, pbar):
    async with aiosqlite.connect(db_path, timeout=60.0) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        with open("pipeline_checkpoint.jsonl", "a") as f:
            while True:
                res = await results_queue.get()
                if res is None:
                    results_queue.task_done()
                    break

                email_id, raw_text, golden_record, persona_v4, dpbc, status, error_log = res

                checkpoint_data = {
                    "email_id": email_id,
                    "status": status,
                    "record": golden_record.model_dump()
                    if golden_record and hasattr(golden_record, "model_dump")
                    else str(golden_record)
                    if golden_record
                    else None,
                    "error": error_log,
                    "occupancy": occupancy_snapshot(),
                }
                f.write(json.dumps(checkpoint_data) + "\n")
                f.flush()

                if status == "completed":
                    await db.execute(
                        """INSERT INTO golden_dataset
                           (raw_email_id, original_text, synthetic_text, target_persona, kda_winner_mutation_id, tone_score, conciseness_score, accuracy_score)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            email_id,
                            raw_text,
                            golden_record.final_prompt_text
                            if hasattr(golden_record, "final_prompt_text")
                            else str(golden_record),
                            persona_v4.typology_classification,
                            golden_record.id if hasattr(golden_record, "id") else "mut_v4_winner",
                            dpbc.tone_target,
                            dpbc.conciseness_target,
                            dpbc.accuracy_target,
                        ),
                    )
                    await db.execute(
                        "UPDATE raw_emails SET status='completed' WHERE id=?", (email_id,)
                    )
                else:
                    await db.execute(
                        "UPDATE raw_emails SET status='failed', error_log=? WHERE id=?",
                        (error_log, email_id),
                    )

                await db.commit()
                pbar.update(1)
                results_queue.task_done()


async def main():
    configure(email_seats=EMAIL_WORKERS)
    print(
        "🚀 Engine v4 Mass Evolution — GPU occupancy mode "
        f"(email_workers/seats={EMAIL_WORKERS}, snapshot={occupancy_snapshot()})"
    )
    orchestrator_v4 = GoldenDatasetOrchestratorV4()
    sampler = DiversitySampler(DB_PATH)

    task_queue = asyncio.Queue(maxsize=EMAIL_WORKERS * 3)
    results_queue = asyncio.Queue()

    async with aiosqlite.connect(DB_PATH, timeout=60.0) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM raw_emails WHERE status='backtranslated' "
            "AND id NOT IN (SELECT raw_email_id FROM golden_dataset)"
        ) as cursor:
            row = await cursor.fetchone()
            total_pending = row[0] if row else 0

    pbar = tqdm(total=total_pending, desc="Engine v4 Queue Evolution", unit="email")

    consumer = asyncio.create_task(consumer_task(results_queue, DB_PATH, pbar))

    workers = [
        asyncio.create_task(worker_task(i, orchestrator_v4, task_queue, results_queue))
        for i in range(EMAIL_WORKERS)
    ]

    BATCH_SIZE = 100
    while True:
        pending_rows = await asyncio.to_thread(sampler.get_next_batch, BATCH_SIZE)
        if not pending_rows:
            break
        for row in pending_rows:
            await task_queue.put(row)

    for _ in range(EMAIL_WORKERS):
        await task_queue.put(None)

    await asyncio.gather(*workers)
    await results_queue.put(None)
    await consumer
    pbar.close()
    print("\n🎯 Engine v4 Mass Evolution Complete!")


if __name__ == "__main__":
    asyncio.run(main())
