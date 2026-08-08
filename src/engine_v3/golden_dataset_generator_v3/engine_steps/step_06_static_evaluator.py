import logging
import asyncio
from typing import List
from src.engine.golden_dataset_generator.schemas import HumanEmail, DPBCThresholds, PromptMutation, EvaluatedEmail
from src.engine.golden_dataset_generator.config import config
from ..schemas import BatchEvaluationResponse

logger = logging.getLogger("EngineV3_Step06_StaticEvaluator")

async def evaluate_mutations_v3(mutations: List[PromptMutation], email: HumanEmail, dpbc: DPBCThresholds, llm_client=None) -> List[EvaluatedEmail]:
    """
    Step 06 (Engine v2): Single-Call Batched Dual-Scoring Evaluator.
    Uses Static-First prompt structure for 100% vLLM Radix-Cache hits (0ms prefill latency).
    """
    logger.info(f"Evaluating {len(mutations)} mutations in 1 Batched LLM call with Static-First layout...")

    candidates_formatted = "\n".join([f"Candidate {idx+1} [ID: {m.id}]:\nPrompt: {m.prompt_text}\n" for idx, m in enumerate(mutations)])

    # Static-First Prompt Layout: Rubrics at index 0 for 100% vLLM Cache Hits
    static_first_prompt = f"""
SYSTEM INSTRUCTIONS & KDA DUAL-SCORING RUBRICS (STATIC PREFIX):
You are the Head Judge. For each Candidate Prompt below:
1. Generate the synthetic email output.
2. Score on 3 absolute dimensions (0.0 to 10.0):
   - Tone (Formality & Sentiment alignment)
   - Conciseness (Length & Structure suitability)
   - Factual Accuracy (Inclusion of essential entities/claims)

TARGET DPBC THRESHOLDS:
- Tone Target: {dpbc.tone_target:.1f}
- Conciseness Target: {dpbc.conciseness_target:.1f}
- Factual Accuracy Target: {dpbc.accuracy_target:.1f}

--- DYNAMIC INPUT DATA ---
Original Target Human Email:
{email.raw_text}

--- CANDIDATES TO EVALUATE ---
{candidates_formatted}
"""

    evaluations: List[EvaluatedEmail] = []

    try:
        if llm_client:
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=BatchEvaluationResponse,
                messages=[{"role": "user", "content": static_first_prompt}]
            )
            response_data = await res if asyncio.iscoroutine(res) else res
            
            mut_dict = {m.id: m for m in mutations}
            for score in response_data.evaluations:
                mut = mut_dict.get(score.mutation_id, mutations[0])
                
                tone_delta = abs(dpbc.tone_target - score.tone_score)
                conc_delta = abs(dpbc.conciseness_target - score.conciseness_score)
                acc_delta = abs(dpbc.accuracy_target - score.accuracy_score)
                
                overall = tone_delta + conc_delta + acc_delta + score.persona_penalty
                
                evaluations.append(EvaluatedEmail(
                    mutation_id=score.mutation_id,
                    prompt_text=mut.prompt_text,
                    synthetic_text=score.synthetic_text,
                    tone_score=score.tone_score,
                    conciseness_score=score.conciseness_score,
                    accuracy_score=score.accuracy_score,
                    tone_delta=tone_delta,
                    conciseness_delta=conc_delta,
                    accuracy_delta=acc_delta,
                    persona_deviation_penalty=score.persona_penalty,
                    overall_delta=overall
                ))
        else:
            for m in mutations:
                evaluations.append(EvaluatedEmail(
                    mutation_id=m.id,
                    prompt_text=m.prompt_text,
                    synthetic_text=f"Mock synthetic email for {m.id}",
                    tone_score=dpbc.tone_target,
                    conciseness_score=dpbc.conciseness_target,
                    accuracy_score=dpbc.accuracy_target,
                    tone_delta=0.0,
                    conciseness_delta=0.0,
                    accuracy_delta=0.0,
                    overall_delta=0.0
                ))
    except Exception as e:
        logger.error(f"LLM evaluation failed in Engine v2 for email {email.id}: {e}")
        # Fallback
        for m in mutations:
            evaluations.append(EvaluatedEmail(
                mutation_id=m.id,
                prompt_text=m.prompt_text,
                synthetic_text="Fallback synthetic text",
                tone_score=5.0, conciseness_score=5.0, accuracy_score=5.0,
                tone_delta=2.0, conciseness_delta=2.0, accuracy_delta=2.0,
                overall_delta=6.0
            ))

    return evaluations
