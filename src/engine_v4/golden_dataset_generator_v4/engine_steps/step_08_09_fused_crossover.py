import uuid
import logging
import asyncio
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
from src.engine.golden_dataset_generator.schemas import KDAMatrix, SuperPrompt, EvaluatedEmail, HumanEmail, JudgeFeedback
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV4, FusedCritiqueAndCrossoverResponse
from ..gpu_occupancy import llm_slot

logger = logging.getLogger("EngineV4_OptionA_FusedCrossover")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception), reraise=True)
async def generate_fused_critique_and_crossover_v4(kda: KDAMatrix, persona: PersonaProfileV4, human_email: HumanEmail, llm_client=None) -> tuple:
    """
    Engine v2 Option A: Fused Critique & Genetic Crossover in 1 Call with Strict Anti-Verbatim Guard.
    """
    eval_dict: Dict[str, EvaluatedEmail] = {e.mutation_id: e for e in kda.evaluations}
    base_winner = eval_dict[kda.overall_winner_mutation_id]

    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    # 100% Static System Prompt for vLLM Prefix Caching
    system_prompt = """
SYSTEM INSTRUCTIONS (STATIC PREFIX):
You are acting as the Head Linguistic Judge AND Genetic Crossover Engine.
TASK PART 1: Critique why the winning synthetic output failed to achieve 0.0 Delta.
TASK PART 2: Synthesize a brand new SuperPrompt merging donor DNA and fixing Part 1 critique.

ANTI-VERBATIM COPYING GUARD: You are STRICTLY FORBIDDEN from copy-pasting or quoting verbatim sentences from the target email inside single/double quotes (NEVER write phrases like "Ensure you state: '...'"). Abstract the user's situation, key entities/dates, intent, and tone naturally into realistic human instructional phrasing.
ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
"""

    # All Dynamic Data and Strict Constraints injected here
    user_prompt = f"""
CRITICAL ACTION CONSTRAINT:
The action command MUST start with EXACTLY ONE of these verbs: {required_verbs}.

TARGET PERSONA CONSTRAINTS:
{persona.model_dump_json(indent=2)}

DONOR DNA:
1. Base Architecture Winner: "{eval_dict[kda.overall_winner_mutation_id].prompt_text}"
2. Best Tone Winner: "{eval_dict[kda.best_tone_mutation_id].prompt_text}"
3. Best Conciseness Winner: "{eval_dict[kda.best_conciseness_mutation_id].prompt_text}"
4. Best Factual Accuracy Winner: "{eval_dict[kda.best_accuracy_mutation_id].prompt_text}"

--- DYNAMIC INPUT DATA ---
Original Email: {human_email.raw_text}
Winning Synthetic Output: {base_winner.synthetic_text}
Current Winner Error Delta: {base_winner.overall_delta:.2f}
"""

    feedback_text = "Delta critique completed."
    final_prompt_text = base_winner.prompt_text

    if llm_client:
        async with llm_slot():
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=FusedCritiqueAndCrossoverResponse,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            response = await res if asyncio.iscoroutine(res) else res
        feedback_text = response.judge_critique
        final_prompt_text = f"{response.action_command} {response.context_details}"
    else:
        feedback_text = "Mock Fused Critique Option A"
        final_prompt_text = f"Draft a concise workplace email to achieve intent: {persona.intent}"

    judge_feedback = JudgeFeedback(
        kda_matrix_id=f"kda_gen_{kda.generation_num}",
        feedback_text=feedback_text
    )

    super_prompt = SuperPrompt(
        id=f"Super_P_OptionA_Gen_{kda.generation_num}_{uuid.uuid4().hex[:4]}",
        base_mutation_id=kda.overall_winner_mutation_id,
        injected_traits={
            "tone": kda.best_tone_mutation_id,
            "conciseness": kda.best_conciseness_mutation_id,
            "accuracy": kda.best_accuracy_mutation_id
        },
        final_prompt_text=final_prompt_text,
        elo_delta=base_winner.overall_delta,
        is_champion=True
    )

    return judge_feedback, super_prompt

# Alias for standard orchestrator


