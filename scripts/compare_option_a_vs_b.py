import sys
import os
import time
import asyncio
import sqlite3
import logging
from typing import List, Dict, Any

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine_v2.golden_dataset_generator_v2.orchestrator_v2 import GoldenDatasetOrchestratorV2
from src.engine.golden_dataset_generator.schemas import HumanEmail, GenerationState, EvaluatedEmail, KDAMatrix, SuperPrompt
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH

logging.basicConfig(level=logging.WARNING)

async def run_option_a(orch_v2, email_id: int, original_text: str, persona, dpbc) -> SuperPrompt:
    """Runs Engine v2 Option A (Fused 1-Call + Anti-Verbatim Guard)."""
    state = GenerationState(human_email_id=str(email_id))
    human_email = HumanEmail(id=str(email_id), raw_text=original_text)

    mutations = await orch_v2._step_05_batch_genesis(human_email, persona)
    evaluations = await orch_v2._step_06_static_evaluate(mutations, human_email, dpbc)
    kda_matrix = orch_v2._step_07_kda_ranking(evaluations, 0)

    # Option A: Fused Step 8/9
    from src.engine_v2.golden_dataset_generator_v2.engine_steps.step_08_09_fused_crossover import generate_fused_critique_and_crossover_v2_option_a
    _, super_prompt_a = await generate_fused_critique_and_crossover_v2_option_a(kda_matrix, persona, human_email, llm_client=orch_v2.llm_client)
    return super_prompt_a

async def run_option_b(orch_v2, email_id: int, original_text: str, persona, dpbc) -> SuperPrompt:
    """Runs Engine v2 Option B (Clean Structural Decoupling Step 8 / Step 9)."""
    state = GenerationState(human_email_id=str(email_id))
    human_email = HumanEmail(id=str(email_id), raw_text=original_text)

    mutations = await orch_v2._step_05_batch_genesis(human_email, persona)
    evaluations = await orch_v2._step_06_static_evaluate(mutations, human_email, dpbc)
    kda_matrix = orch_v2._step_07_kda_ranking(evaluations, 0)

    # Option B: Decoupled Step 8 & Step 9
    from src.engine_v2.golden_dataset_generator_v2.engine_steps.step_08_feedback_loop_v2 import generate_judge_feedback_v2_option_b
    from src.engine_v2.golden_dataset_generator_v2.engine_steps/step_09_crossover_v2 import generate_crossover_v2_option_b
    
    feedback_b = await generate_judge_feedback_v2_option_b(kda_matrix, persona, human_email, llm_client=orch_v2.llm_client)
    super_prompt_b = await generate_crossover_v2_option_b(kda_matrix, feedback_b, persona, llm_client=orch_v2.llm_client)
    return super_prompt_b

async def main():
    print("="*90)
    print("🔬 COMPARATIVE BENCHMARK: ENGINE V2 OPTION A (FUSED+GUARD) VS OPTION B (DECOUPLED)")
    print("="*90)

    # Load 5 real emails from pipeline.db
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, clean_text, raw_text FROM raw_emails WHERE status='backtranslated' LIMIT 5")
    rows = c.fetchall()
    conn.close()

    real_emails = []
    for r in rows:
        text = r[1] if (r[1] and len(r[1].strip('- \n\t')) >= 10) else r[2]
        if text:
            real_emails.append((r[0], text[:4000]))

    orch_v2 = GoldenDatasetOrchestratorV2()

    a_results = []
    b_results = []

    for idx, (e_id, text) in enumerate(real_emails):
        human_email = orch_v2._step_01_ingest(text, str(e_id))
        persona_v2 = await orch_v2._step_02_extract_persona(human_email)
        dpbc = orch_v2._step_03_get_dpbc_thresholds(persona_v2, human_email)

        # Run Option A
        t0 = time.time()
        sp_a = await run_option_a(orch_v2, e_id, text, persona_v2, dpbc)
        time_a = time.time() - t0

        # Run Option B
        t0 = time.time()
        sp_b = await run_option_b(orch_v2, e_id, text, persona_v2, dpbc)
        time_b = time.time() - t0

        a_results.append({"id": e_id, "time": time_a, "prompt": sp_a.final_prompt_text, "delta": sp_a.elo_delta})
        b_results.append({"id": e_id, "time": time_b, "prompt": sp_b.final_prompt_text, "delta": sp_b.elo_delta})

        print(f"\n📌 REAL EMAIL RECORD ID: {e_id}")
        print(f"  Raw Target Text snippet: \"{text[:80]}...\"")
        print(f"\n  🔹 OPTION A (Fused + Prompt Guard) | Latency: {time_a:.2f}s | Delta: {sp_a.elo_delta:.4f}")
        print(f"     Super Prompt: {sp_a.final_prompt_text}")
        print(f"\n  🔸 OPTION B (Structural Decoupling) | Latency: {time_b:.2f}s | Delta: {sp_b.elo_delta:.4f}")
        print(f"     Super Prompt: {sp_b.final_prompt_text}")
        print("-" * 90)

    # METRICS SUMMARY
    avg_time_a = sum(r['time'] for r in a_results) / len(a_results)
    avg_time_b = sum(r['time'] for r in b_results) / len(b_results)
    avg_delta_a = sum(r['delta'] for r in a_results) / len(a_results)
    avg_delta_b = sum(r['delta'] for r in b_results) / len(b_results)

    print("\n" + "="*90)
    print("📊 FINAL OPTION A VS OPTION B METRICS SUMMARY")
    print("="*90)
    print(f"Option A (Fused + Guard)      : Avg Time = {avg_time_a:.2f}s / email | Avg Delta = {avg_delta_a:.4f} | Total LLM Calls = 3")
    print(f"Option B (Structural Decoup)  : Avg Time = {avg_time_b:.2f}s / email | Avg Delta = {avg_delta_b:.4f} | Total LLM Calls = 4")

if __name__ == "__main__":
    asyncio.run(main())
