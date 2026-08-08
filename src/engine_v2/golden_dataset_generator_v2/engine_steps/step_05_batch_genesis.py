import uuid
import logging
import asyncio
from typing import List
from src.engine.golden_dataset_generator.schemas import HumanEmail, PromptMutation
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV2, BatchGenesisResponse

logger = logging.getLogger("EngineV2_Step05_BatchGenesis")

async def generate_batch_genesis_mutations(email: HumanEmail, persona: PersonaProfileV2, llm_client=None) -> List[PromptMutation]:
    """
    Step 05 (Engine v2): 1-Call Batched Genesis Candidate Generation.
    Generates 5 distinct Base Prompts in 1 single LLM call with Static-First prompt structure.
    """
    logger.info(f"Generating 5 Genesis Mutations in 1 Batched LLM call for Email ID: {email.id}")

    category_verbs = {
        "Zero-Shot Drafting": "'Write', 'Draft', or 'Generate'",
        "Data Extraction": "'Extract', 'List', or 'Find'",
        "Thread Summarization": "'Summarize', 'Brief', or 'Catch me up'",
        "Tone Translation": "'Rewrite', 'Translate', or 'Make this sound'"
    }
    required_verbs = category_verbs.get(persona.nlp_task, "'Write', 'Draft', or 'Generate'")

    # Static-First Prompt Layout: Instructions at index 0 for 100% vLLM Radix Cache Hits
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
Strategies to implement: {persona.prompting_strategies}
Target Email Text: {email.raw_text}
"""

    mutations: List[PromptMutation] = []

    try:
        if llm_client:
            res = llm_client.chat.completions.create(
                model=config.DEFAULT_GENERATION_MODEL,
                response_model=BatchGenesisResponse,
                messages=[{"role": "user", "content": static_first_prompt}]
            )
            response_data = await res if asyncio.iscoroutine(res) else res
            
            for idx, item in enumerate(response_data.mutations[:5]):
                mutations.append(PromptMutation(
                    id=f"mut_v2_gen0_{idx}_{uuid.uuid4().hex[:4]}",
                    typology_persona=item.p_strategy,
                    prompt_text=f"{item.action_command} {item.context_details}",
                    generation_num=0
                ))
        else:
            for idx, p_strat in enumerate(persona.prompting_strategies[:5]):
                mutations.append(PromptMutation(
                    id=f"mut_v2_gen0_{idx}_{uuid.uuid4().hex[:4]}",
                    typology_persona=p_strat,
                    prompt_text=f"Write an email using strategy {p_strat} to achieve intent: {persona.intent}",
                    generation_num=0
                ))
    except Exception as e:
        logger.error(f"LLM failed in Engine v2 Batched Genesis for email {email.id}: {e}")

    return mutations
