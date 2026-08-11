import logging
import asyncio
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
from src.engine.golden_dataset_generator.schemas import HumanEmail, DPBCThresholds, PromptMutation, EvaluatedEmail
from src.engine.golden_dataset_generator.config import config
from ..schemas import SingleCandidateScore

logger = logging.getLogger("EngineV4_Step06_StaticEvaluator")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception), reraise=True)
async def evaluate_mutations_v4(mutations: List[PromptMutation], email: HumanEmail, dpbc: DPBCThresholds, llm_client=None) -> List[EvaluatedEmail]:
    """
    Step 06 (Engine v2): Single-Call Batched Dual-Scoring Evaluator.
    Uses Static-First prompt structure for 100% vLLM Radix-Cache hits (0ms prefill latency).
    """
    logger.info(f"Evaluating {len(mutations)} mutations concurrently with Static-First layout...")

    # 100% Static System Prompt for vLLM Prefix Caching
    system_prompt = """
SYSTEM INSTRUCTIONS & KDA DUAL-SCORING RUBRICS (STATIC PREFIX):
You are the Head Judge. For the Candidate Prompt below:
1. Generate the synthetic email output.
2. Score on 3 absolute dimensions (0.0 to 10.0):
   - Tone (Formality & Sentiment alignment)
   - Conciseness (Length & Structure suitability)
   - Factual Accuracy (Inclusion of essential entities/claims)
"""

    async def _eval_single(m: PromptMutation) -> EvaluatedEmail:
        user_prompt = f"""
TARGET DPBC THRESHOLDS:
- Tone Target: {dpbc.tone_target:.1f}
- Conciseness Target: {dpbc.conciseness_target:.1f}
- Factual Accuracy Target: {dpbc.accuracy_target:.1f}

--- DYNAMIC INPUT DATA ---
Original Target Human Email:
{email.raw_text}

--- CANDIDATE TO EVALUATE ---
Candidate [ID: {m.id}]:
Prompt: {m.prompt_text}
"""
        if llm_client:
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=SingleCandidateScore,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            score = await res if asyncio.iscoroutine(res) else res
            
            tone_delta = abs(dpbc.tone_target - score.tone_score)
            conc_delta = abs(dpbc.conciseness_target - score.conciseness_score)
            acc_delta = abs(dpbc.accuracy_target - score.accuracy_score)
            overall = tone_delta + conc_delta + acc_delta + score.persona_penalty
            
            return EvaluatedEmail(
                mutation_id=score.mutation_id,
                prompt_text=m.prompt_text,
                synthetic_text=score.synthetic_text,
                tone_score=score.tone_score,
                conciseness_score=score.conciseness_score,
                accuracy_score=score.accuracy_score,
                tone_delta=tone_delta,
                conciseness_delta=conc_delta,
                accuracy_delta=acc_delta,
                persona_deviation_penalty=score.persona_penalty,
                overall_delta=overall
            )
        else:
            return EvaluatedEmail(
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
            )

    evaluations = await asyncio.gather(*[_eval_single(m) for m in mutations])
    return list(evaluations)
