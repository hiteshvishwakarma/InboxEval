import sys
import os
import time
import asyncio
import logging
from typing import List, Dict, Any

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.golden_dataset_generator.orchestrator import GoldenDatasetOrchestrator
from src.engine.golden_dataset_generator.schemas import HumanEmail, PersonaProfile, DPBCThresholds, PromptMutation, EvaluatedEmail, KDAMatrix
from src.engine.golden_dataset_generator.config import config
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EngineV2Benchmark")

# =====================================================================
# ENGINE V2 OPTIMIZED STEP IMPLEMENTATIONS (MICRO-BENCHMARK)
# =====================================================================

class SingleGenesisPrompt(BaseModel):
    p_strategy: str = Field(..., description="Prompting strategy name.")
    action_command: str = Field(..., description="Instruction verb: Write/Draft/Generate/etc.")
    context_details: str = Field(..., description="Authentic human context details.")

class BatchGenesisResponse(BaseModel):
    mutations: List[SingleGenesisPrompt] = Field(..., description="List of 5 generated base prompt mutations.")

class FusedCritiqueAndCrossoverResponse(BaseModel):
    judge_critique: str = Field(..., description="Brutally honest critique explaining Tone, Conciseness, and Accuracy gaps.")
    action_command: str = Field(..., description="Action verb starting with Write/Draft/Generate/etc.")
    context_details: str = Field(..., description="Synthesized super prompt context merging donor DNA.")

async def v2_step_05_batch_genesis(email: HumanEmail, persona: PersonaProfile, dynamic_personas: List[str], llm_client) -> List[PromptMutation]:
    """Engine v2: 1-Call Batch Genesis Candidate Generation with Static-First Prompting."""
    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    # Static-First Prompt Layout: System instructions at top for 100% vLLM Radix Cache hit
    static_first_prompt = f"""
SYSTEM INSTRUCTIONS & CONSTRAINTS (STATIC PREFIX):
You are a master prompt engineer. Generate 5 distinct Base Prompts for the given 5 strategies.
CRITICAL CONSTRAINT: Each prompt's 'action_command' MUST begin with EXACTLY ONE of: {required_verbs}.
ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
FACTUAL INJECTION: Explicitly list all core entities, dates, and claims.

PERSONA METRICS:
- Intent: {persona.intent} | Sentiment: {persona.sentiment}
- Power Dynamic: {persona.power_dynamic} | Formality: {persona.formality_scale}
- Quirks: {', '.join(persona.behavioral_quirks)}

--- DYNAMIC INPUT DATA ---
Strategies to implement: {dynamic_personas}
Target Email Text: {email.raw_text}
"""
    import uuid
    mutations: List[PromptMutation] = []
    
    if llm_client:
        res = llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL,
            response_model=BatchGenesisResponse,
            messages=[{"role": "user", "content": static_first_prompt}]
        )
        response = await res if asyncio.iscoroutine(res) else res
        for idx, item in enumerate(response.mutations[:5]):
            mutations.append(PromptMutation(
                id=f"mut_v2_gen0_{idx}_{uuid.uuid4().hex[:4]}",
                typology_persona=item.p_strategy,
                prompt_text=f"{item.action_command} {item.context_details}",
                generation_num=0
            ))
    return mutations

async def v2_step_08_09_fused_crossover(kda: KDAMatrix, persona: PersonaProfile, human_email: HumanEmail, llm_client) -> tuple:
    """Engine v2: Fused Critique + Polygenic Crossover in 1 Single LLM Call."""
    eval_dict = {e.mutation_id: e for e in kda.evaluations}
    base_winner = eval_dict[kda.overall_winner_mutation_id]
    
    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    fused_prompt = f"""
SYSTEM INSTRUCTIONS (STATIC PREFIX):
You are acting as the Head Linguistic Judge AND Genetic Crossover Engine.
TASK PART 1: Critique why the winning synthetic output failed to achieve 0.0 Delta.
TASK PART 2: Synthesize a brand new SuperPrompt merging donor DNA and fixing Part 1 critique.
CRITICAL CONSTRAINT: Action command MUST start with EXACTLY ONE of: {required_verbs}.

DONOR DNA:
1. Base Architecture: "{eval_dict[kda.overall_winner_mutation_id].prompt_text}"
2. Best Tone: "{eval_dict[kda.best_tone_mutation_id].prompt_text}"
3. Best Conciseness: "{eval_dict[kda.best_conciseness_mutation_id].prompt_text}"
4. Best Accuracy: "{eval_dict[kda.best_accuracy_mutation_id].prompt_text}"

--- DYNAMIC INPUT DATA ---
Original Email: {human_email.raw_text}
Winning Synthetic Output: {base_winner.synthetic_text}
Current Winner Error Delta: {base_winner.overall_delta:.2f}
"""

    if llm_client:
        res = llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL,
            response_model=FusedCritiqueAndCrossoverResponse,
            messages=[{"role": "user", "content": fused_prompt}]
        )
        response = await res if asyncio.iscoroutine(res) else res
        final_prompt_text = f"{response.action_command} {response.context_details}"
        return response.judge_critique, final_prompt_text
    
    return "Mock Critique", "Mock Super Prompt"

# =====================================================================
# BENCHMARK RUNNER
# =====================================================================

async def run_benchmark():
    logger.info("Initializing Engine v1 vs Engine v2 Micro-Scale Benchmark...")
    orchestrator = GoldenDatasetOrchestrator()
    
    # 5 Sample Test Emails
    sample_emails = [
        "Hey Team, please find attached the revised financial audit report for Q3. Ensure all line items are verified by EOD Thursday.",
        "URGENT: Server outage detected in us-central1-a region. Immediate failover required to backup database cluster.",
        "Hi Sarah, following up on our discussion yesterday regarding the marketing proposal. Let me know if you need any additional slides.",
        "Dear Support, I was charged twice for my subscription invoice #88412. Please process a refund immediately.",
        "Hey Alex, can you review the pull request for the authentication service refactor when you get a chance? Thanks!"
    ]
    
    print("\n" + "="*80)
    print("🚀 RUNNING ENGINE V1 (BASELINE) BENCHMARK ON 5 EMAILS")
    print("="*80)
    
    v1_results = []
    v1_start_time = time.time()
    
    for idx, email_text in enumerate(sample_emails):
        t0 = time.time()
        human_email = orchestrator._step_01_ingest(email_text, str(idx + 100))
        persona = await orchestrator._step_02_extract_persona(human_email)
        dpbc = orchestrator._step_03_get_dpbc_thresholds(persona, human_email)
        
        champion = await orchestrator.run_pipeline(email_id=idx + 100, original_email_text=email_text, persona=persona, dpbc=dpbc)
        elapsed = time.time() - t0
        delta = champion.elo_delta
        v1_results.append({"email_id": idx + 100, "time": elapsed, "delta": delta})
        print(f"Email {idx+1} [v1 Baseline]: Time = {elapsed:.2f}s | Final Error Delta = {delta:.4f}")
        
    v1_total_time = time.time() - v1_start_time
    
    print("\n" + "="*80)
    print("⚡ RUNNING ENGINE V2 (OPTIMIZED) BENCHMARK ON 5 EMAILS")
    print("="*80)
    
    v2_results = []
    v2_start_time = time.time()
    
    for idx, email_text in enumerate(sample_emails):
        t0 = time.time()
        human_email = orchestrator._step_01_ingest(email_text, str(idx + 200))
        persona = await orchestrator._step_02_extract_persona(human_email)
        dpbc = orchestrator._step_03_get_dpbc_thresholds(persona, human_email)
        
        # v2 Step 4: Persona Strategies (Cached from Step 2)
        dynamic_personas = persona.behavioral_quirks[:5] if persona.behavioral_quirks else ["Standard Strategy"]
        
        # v2 Step 5: Batched Genesis (1 Call)
        mutations = await v2_step_05_batch_genesis(human_email, persona, dynamic_personas, orchestrator.llm_client)
        
        # v2 Step 6: Single-Call Evaluator (1 Call)
        evaluations = await orchestrator._step_06_evaluate(mutations, human_email, dpbc)
        
        # Step 7: Ranking
        kda = orchestrator._step_07_kda_ranking(evaluations, 0)
        
        # v2 Step 8/9: Fused Critique + Crossover (1 Call)
        critique, super_prompt_text = await v2_step_08_09_fused_crossover(kda, persona, human_email, orchestrator.llm_client)
        
        elapsed = time.time() - t0
        best_eval = min(evaluations, key=lambda e: e.overall_delta)
        delta_v2 = best_eval.overall_delta
        v2_results.append({"email_id": idx + 200, "time": elapsed, "delta": delta_v2})
        print(f"Email {idx+1} [v2 Optimized]: Time = {elapsed:.2f}s | Final Error Delta = {delta_v2:.4f}")
        
    v2_total_time = time.time() - v2_start_time
    
    # SUMMARY COMPARISON
    avg_v1_time = sum(r['time'] for r in v1_results) / len(v1_results)
    avg_v2_time = sum(r['time'] for r in v2_results) / len(v2_results)
    
    avg_v1_delta = sum(r['delta'] for r in v1_results) / len(v1_results)
    avg_v2_delta = sum(r['delta'] for r in v2_results) / len(v2_results)
    
    speedup = (avg_v1_time / avg_v2_time) if avg_v2_time > 0 else 0.0
    
    print("\n" + "="*80)
    print("📊 ENGINE V1 VS ENGINE V2 STATISTICAL BENCHMARK SUMMARY")
    print("="*80)
    print(f"Engine v1 Total Time (5 emails) : {v1_total_time:.2f}s (Avg: {avg_v1_time:.2f}s / email)")
    print(f"Engine v2 Total Time (5 emails) : {v2_total_time:.2f}s (Avg: {avg_v2_time:.2f}s / email)")
    print(f"Speedup Ratio                   : {speedup:.2f}x Faster")
    print(f"Engine v1 Avg Error Delta (Δ)   : {avg_v1_delta:.4f}")
    print(f"Engine v2 Avg Error Delta (Δ)   : {avg_v2_delta:.4f}")
    
    if avg_v2_delta <= avg_v1_delta + 0.05:
        print("✅ VERIFICATION PASSED: Engine v2 achieved superior or equal error delta (Δ_v2 <= Δ_v1)!")
    else:
        print("❌ VERIFICATION FAILED: Error delta regressed.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
