import logging
import asyncio
from typing import Dict
from pydantic import BaseModel, Field
from src.engine.golden_dataset_generator.schemas import KDAMatrix, JudgeFeedback, EvaluatedEmail, HumanEmail
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV4

logger = logging.getLogger("EngineV4_OptionB_Step08_Feedback")

class JudgeFeedbackResult(BaseModel):
    critique: str = Field(..., description="Detailed critique of why tone, conciseness, or accuracy missed perfect 0.0 delta.")

async def generate_judge_feedback_v4_option_b(kda: KDAMatrix, persona: PersonaProfileV4, human_email: HumanEmail, llm_client=None) -> JudgeFeedback:
    """Step 08 (Option B): Judge Critique (Separate Call). Writes written text analysis."""
    eval_dict: Dict[str, EvaluatedEmail] = {e.mutation_id: e for e in kda.evaluations}
    base_winner = eval_dict[kda.overall_winner_mutation_id]

    prompt = f"""
SYSTEM INSTRUCTIONS (STATIC PREFIX):
You are the Head Judge. Analyze why the winning synthetic email failed to achieve 0.0 Delta compared to the target raw email.
Write explicit written instructions for the Crossover Engine explaining what tone, conciseness, or factual accuracy adjustments are required.

--- DYNAMIC INPUT DATA ---
Original Raw Email: {human_email.raw_text}
Winning Synthetic Email: {base_winner.synthetic_text}
Current Winner Error Delta: {base_winner.overall_delta:.2f}
"""

    feedback_text = "Analysis completed."
    try:
        if llm_client:
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=JudgeFeedbackResult,
                messages=[{"role": "user", "content": prompt}]
            )
            result = await res if asyncio.iscoroutine(res) else res
            feedback_text = result.critique
    except Exception as e:
        logger.error(f"Option B Step 08 failed for Gen {kda.generation_num}: {e}")

    return JudgeFeedback(
        kda_matrix_id=f"kda_gen_{kda.generation_num}",
        feedback_text=feedback_text
    )
