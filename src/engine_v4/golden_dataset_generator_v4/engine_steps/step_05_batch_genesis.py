import uuid
import logging
import asyncio
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.engine.golden_dataset_generator.schemas import HumanEmail, PromptMutation
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV4, SingleGenesisPrompt
from ..gpu_occupancy import genesis_fanout, llm_slot

logger = logging.getLogger("EngineV4_Step05_BatchGenesis")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception), reraise=True)
async def generate_batch_genesis_mutations(
    email: HumanEmail,
    persona: PersonaProfileV4,
    llm_client=None,
    size_category: Optional[str] = None,
) -> List[PromptMutation]:
    """
    Step 05: size-aware parallel genesis with global LLM slot budgeting.
    Static system prefix preserved for vLLM prefix caching.
    """
    strategies = list(persona.prompting_strategies or [])
    n = genesis_fanout(size_category, len(strategies) if strategies else 5)
    if not strategies:
        strategies = [f"strategy_{i}" for i in range(n)]
    chosen = strategies[:n]
    logger.info(
        "Generating %s Genesis Mutations for Email ID %s (size=%s)",
        n,
        email.id,
        size_category or "unknown",
    )

    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

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
            async with llm_slot():
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
        return PromptMutation(
            id=f"mut_v4_gen0_{idx}_{uuid.uuid4().hex[:4]}",
            typology_persona=p_strat,
            prompt_text=f"Write an email using strategy {p_strat} to achieve intent: {persona.intent}",
            generation_num=0
        )

    mutations = await asyncio.gather(
        *[_gen_single(idx, p_strat) for idx, p_strat in enumerate(chosen)]
    )
    return list(mutations)
