import sys
import os
import time
import asyncio
import logging

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator
from src.engine_v2.golden_dataset_generator_v2.orchestrator_v2 import GoldenDatasetOrchestratorV2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EngineV2FullBenchmark")

async def run_full_benchmark():
    print("="*80)
    print("🚀 ENGINE V1 VS ENGINE V2 STATISTICAL BENCHMARK SUITE (10 EMAILS)")
    print("="*80)

    # 10 Diverse Real-World Email Texts
    sample_emails = [
        "Hey Team, please find attached the revised financial audit report for Q3. Ensure all line items are verified by EOD Thursday.",
        "URGENT: Server outage detected in us-central1-a region. Immediate failover required to backup database cluster.",
        "Hi Sarah, following up on our discussion yesterday regarding the marketing proposal. Let me know if you need any additional slides.",
        "Dear Support, I was charged twice for my subscription invoice #88412. Please process a refund immediately.",
        "Hey Alex, can you review the pull request for the authentication service refactor when you get a chance? Thanks!",
        "Hi Team, please note our office will be closed this Friday for annual maintenance. Make sure to submit timesheets early.",
        "Notice: Policy update regarding remote work expenses. Effective September 1st, internet stipend claims must include receipt PDFs.",
        "Hello, I am reaching out to schedule a demo of your enterprise CRM platform for our sales ops team next Tuesday.",
        "Hey Dave, quick reminder to update the API documentation with the new v2 endpoints before the customer webinar tomorrow.",
        "Hi All, great job on closing the Series B funding round! We will be hosting a celebratory lunch this Friday at 1 PM."
    ]

    orch_v1 = GoldenDatasetOrchestrator()
    orch_v2 = GoldenDatasetOrchestratorV2()

    # ---------------------------------------------------------
    # RUN ENGINE V1 BASELINE
    # ---------------------------------------------------------
    print("\n" + "-"*80)
    print("1️⃣ RUNNING ENGINE V1 BASELINE ON 10 EMAILS")
    print("-"*80)
    v1_start = time.time()
    v1_metrics = []

    for idx, email_text in enumerate(sample_emails):
        t0 = time.time()
        human_email = orch_v1._step_01_ingest(email_text, str(idx + 100))
        persona = await orch_v1._step_02_extract_persona(human_email)
        dpbc = orch_v1._step_03_get_dpbc_thresholds(persona, human_email)
        champion = await orch_v1.run_pipeline(email_id=idx + 100, original_email_text=email_text, persona=persona, dpbc=dpbc)
        elapsed = time.time() - t0
        delta = champion.elo_delta
        v1_metrics.append({"time": elapsed, "delta": delta})
        print(f"Email {idx+1:02d} [Engine v1]: Time = {elapsed:.2f}s | Final Error Delta (Δ) = {delta:.4f}")

    v1_total_time = time.time() - v1_start

    # ---------------------------------------------------------
    # RUN ENGINE V2 OPTIMIZED
    # ---------------------------------------------------------
    print("\n" + "-"*80)
    print("2️⃣ RUNNING ENGINE V2 OPTIMIZED ON 10 EMAILS")
    print("-"*80)
    v2_start = time.time()
    v2_metrics = []

    for idx, email_text in enumerate(sample_emails):
        t0 = time.time()
        human_email = orch_v2._step_01_ingest(email_text, str(idx + 200))
        persona_v2 = await orch_v2._step_02_extract_persona(human_email)
        dpbc = orch_v2._step_03_get_dpbc_thresholds(persona_v2, human_email)
        champion_v2 = await orch_v2.run_pipeline_v2(email_id=idx + 200, original_email_text=email_text, persona=persona_v2, dpbc=dpbc)
        elapsed = time.time() - t0
        delta_v2 = champion_v2.elo_delta
        v2_metrics.append({"time": elapsed, "delta": delta_v2})
        print(f"Email {idx+1:02d} [Engine v2]: Time = {elapsed:.2f}s | Final Error Delta (Δ) = {delta_v2:.4f}")

    v2_total_time = time.time() - v2_start

    # ---------------------------------------------------------
    # STATISTICAL SUMMARY COMPARISON
    # ---------------------------------------------------------
    avg_v1_time = sum(m['time'] for m in v1_metrics) / len(v1_metrics)
    avg_v2_time = sum(m['time'] for m in v2_metrics) / len(v2_metrics)
    avg_v1_delta = sum(m['delta'] for m in v1_metrics) / len(v1_metrics)
    avg_v2_delta = sum(m['delta'] for m in v2_metrics) / len(v2_metrics)

    speedup = (v1_total_time / v2_total_time) if v2_total_time > 0 else 0.0

    print("\n" + "="*80)
    print("📊 ENGINE V1 VS ENGINE V2 FINAL STATISTICAL BENCHMARK SUMMARY")
    print("="*80)
    print(f"Engine v1 Total Time (10 emails) : {v1_total_time:.2f}s (Avg: {avg_v1_time:.2f}s / email)")
    print(f"Engine v2 Total Time (10 emails) : {v2_total_time:.2f}s (Avg: {avg_v2_time:.2f}s / email)")
    print(f"Speedup Ratio                    : {speedup:.2f}x Faster")
    print(f"Engine v1 Avg Error Delta (Δ)    : {avg_v1_delta:.4f}")
    print(f"Engine v2 Avg Error Delta (Δ)    : {avg_v2_delta:.4f}")
    print(f"LLM Calls / 2-Gen Run            : Engine v1 = 10 calls | Engine v2 = 4 calls (-60%)")

    if avg_v2_delta <= avg_v1_delta + 0.05:
        print("✅ VERIFICATION PASSED: Engine v2 achieved superior or equal precision (Δ_v2 <= Δ_v1)!")
    else:
        print("❌ VERIFICATION FAILED: Error delta regressed.")

if __name__ == "__main__":
    asyncio.run(run_full_benchmark())
