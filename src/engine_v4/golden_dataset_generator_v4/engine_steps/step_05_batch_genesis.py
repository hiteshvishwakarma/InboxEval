import uuid
import logging
import asyncio
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
from src.engine.golden_dataset_generator.schemas import HumanEmail, PromptMutation
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV4, SingleGenesisPrompt

logger = logging.getLogger("EngineV4_Step05_BatchGenesis")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception), reraise=True)
async def generate_batch_genesis_mutations(email: HumanEmail, persona: PersonaProfileV4, llm_client=None) -> List[PromptMutation]:
    """
    Step 05 (Engine v2): 1-Call Batched Genesis Candidate Generation.
    Generates 5 distinct Base Prompts in 1 single LLM call with Static-First prompt structure.
    """
    logger.info(f"Generating 5 Genesis Mutations concurrently for Email ID: {email.id}")

    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    # 100% Static System Prompt for vLLM Prefix Caching
    system_prompt = """
SYSTEM INSTRUCTIONS & CONSTRAINTS (STATIC PREFIX):
You are a master prompt engineer. Generate a Base Prompt for the given strategy in the User Prompt.
ANTI-META LEAK: Never refer to 'the original email' or 'reference text'.
FACTUAL INJECTION: Explicitly list all core entities, dates, and claims.
"""

    async def _gen_single(idx: int, p_strat: str) -> PromptMutation:
        user_prompt = f"""
CRITICAL CONSTRAINT: The prompt's 'action_command' MUST begin with EXACTLY ONE of: {required_verbs}.

TARGET PERSONA METRICS:
- Intent: {persona.intent} | Sentiment: {persona.sentiment}
- Power Dynamic: {persona.power_dynamic} | Formality: {persona.formality_scale}
- Quirks: {', '.join(persona.behavioral_quirks)}

--- DYNAMIC INPUT DATA ---
Strategy to implement: {p_strat}
Target Email Text: {email.raw_text}
"""
        if llm_client:
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=SingleGenesisPrompt,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            item = await res if asyncio.iscoroutine(res) else res
            return PromptMutation(
                id=f"mut_v4_gen0_{idx}_{uuid.uuid4().hex[:4]}",
                typology_persona=item.p_strategy,
                prompt_text=f"{item.action_command} {item.context_details}",
                generation_num=0
            )
        else:
            return PromptMutation(
                id=f"mut_v4_gen0_{idx}_{uuid.uuid4().hex[:4]}",
                typology_persona=p_strat,
                prompt_text=f"Write an email using strategy {p_strat} to achieve intent: {persona.intent}",
                generation_num=0
            )

    mutations = await asyncio.gather(*[_gen_single(idx, p_strat) for idx, p_strat in enumerate(persona.prompting_strategies[:5])])
    return list(mutations)
