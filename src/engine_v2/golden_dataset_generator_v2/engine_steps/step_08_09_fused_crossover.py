import uuid
import logging
import asyncio
from typing import Dict, Any
from src.engine.golden_dataset_generator.schemas import KDAMatrix, SuperPrompt, EvaluatedEmail, HumanEmail, JudgeFeedback
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV2, FusedCritiqueAndCrossoverResponse

logger = logging.getLogger("EngineV2_OptionA_FusedCrossover")

async def generate_fused_critique_and_crossover_v2_option_a(kda: KDAMatrix, persona: PersonaProfileV2, human_email: HumanEmail, llm_client=None) -> tuple:
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

    # Static-First Fused Prompt Layout with Strict Anti-Verbatim Guard
    fused_prompt = f"""
SYSTEM INSTRUCTIONS (STATIC PREFIX):
You are acting as the Head Linguistic Judge AND Genetic Crossover Engine.
TASK PART 1: Critique why the winning synthetic output failed to achieve 0.0 Delta.
TASK PART 2: Synthesize a brand new SuperPrompt merging donor DNA and fixing Part 1 critique.

CRITICAL CONSTRAINTS:
1. Action command MUST start with EXACTLY ONE of: {required_verbs}.
2. ANTI-VERBATIM COPYING GUARD: You are STRICTLY FORBIDDEN from copy-pasting or quoting verbatim sentences from the target email inside single/double quotes (NEVER write phrases like "Ensure you state: '...'"). Abstract the user's situation, key entities/dates, intent, and tone naturally into realistic human instructional phrasing.
3. ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.

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

    try:
        if llm_client:
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=FusedCritiqueAndCrossoverResponse,
                messages=[{"role": "user", "content": fused_prompt}]
            )
            response = await res if asyncio.iscoroutine(res) else res
            feedback_text = response.judge_critique
            final_prompt_text = f"{response.action_command} {response.context_details}"
        else:
            feedback_text = "Mock Fused Critique Option A"
            final_prompt_text = f"Draft a concise workplace email to achieve intent: {persona.intent}"
    except Exception as e:
        logger.error(f"Option A LLM failed in Fused Critique/Crossover for Gen {kda.generation_num}: {e}")

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
generate_fused_critique_and_crossover_v2 = generate_fused_critique_and_crossover_v2_option_a

