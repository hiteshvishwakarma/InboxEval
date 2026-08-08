import uuid
import logging
import asyncio
from typing import Dict
from pydantic import BaseModel, Field
from src.engine.golden_dataset_generator.schemas import KDAMatrix, JudgeFeedback, SuperPrompt, EvaluatedEmail
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV3

logger = logging.getLogger("EngineV3_OptionB_Step09_Crossover")

class CrossoverResult(BaseModel):
    action_command: str = Field(..., description="Action verb starting with Write/Draft/Generate/etc.")
    context_details: str = Field(..., description="Synthesized super prompt context merging donor DNA.")

async def generate_crossover_v3_option_b(kda: KDAMatrix, feedback: JudgeFeedback, persona: PersonaProfileV3, llm_client=None) -> SuperPrompt:
    """
    Step 09 (Option B): Structural Decoupling Crossover Synthesis.
    Receives ONLY Donor DNA + Judge Critique text (zero human_email.raw_text input!).
    Inherently impossible to verbatim leak because raw text is completely omitted from the prompt window.
    """
    eval_dict: Dict[str, EvaluatedEmail] = {e.mutation_id: e for e in kda.evaluations}
    base_winner_id = kda.overall_winner_mutation_id
    base_winner = eval_dict[base_winner_id]

    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    # Notice: Zero raw_email.text input in this prompt window!
    crossover_prompt = f"""
SYSTEM INSTRUCTIONS (STATIC PREFIX):
You are a Polygenic Genetic Crossover Engine.
Synthesize a brand new SuperPrompt by merging the 4 winning prompt mutations below and fixing the Judge's feedback.

CRITICAL CONSTRAINTS:
1. Action command MUST start with EXACTLY ONE of: {required_verbs}.
2. ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
3. Do not over-engineer or roboticize the prompt; let the natural human tone of the donors dictate the structure.

DONOR DNA:
1. Base Architecture Winner: "{eval_dict[kda.overall_winner_mutation_id].prompt_text}"
2. Best Tone Winner: "{eval_dict[kda.best_tone_mutation_id].prompt_text}"
3. Best Conciseness Winner: "{eval_dict[kda.best_conciseness_mutation_id].prompt_text}"
4. Best Factual Accuracy Winner: "{eval_dict[kda.best_accuracy_mutation_id].prompt_text}"

--- JUDGE'S CRITIQUE & INSTRUCTIONS ---
"{feedback.feedback_text}"
"""

    final_prompt_text = base_winner.prompt_text

    try:
        if llm_client:
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=CrossoverResult,
                messages=[{"role": "user", "content": crossover_prompt}]
            )
            response = await res if asyncio.iscoroutine(res) else res
            final_prompt_text = f"{response.action_command} {response.context_details}"
        else:
            final_prompt_text = f"Draft a concise workplace message to achieve intent: {persona.intent}"
    except Exception as e:
        logger.error(f"Option B Step 09 LLM failed for Gen {kda.generation_num}: {e}")

    return SuperPrompt(
        id=f"Super_P_OptionB_Gen_{kda.generation_num}_{uuid.uuid4().hex[:4]}",
        base_mutation_id=base_winner_id,
        injected_traits={
            "tone": kda.best_tone_mutation_id,
            "conciseness": kda.best_conciseness_mutation_id,
            "accuracy": kda.best_accuracy_mutation_id
        },
        final_prompt_text=final_prompt_text,
        elo_delta=base_winner.overall_delta,
        is_champion=True
    )
