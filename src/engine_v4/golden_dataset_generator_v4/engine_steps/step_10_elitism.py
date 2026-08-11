import uuid
import logging
import asyncio
from typing import List
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.engine.golden_dataset_generator.schemas import SuperPrompt, PromptMutation
from src.engine.golden_dataset_generator.config import config
from ..schemas import PersonaProfileV4, MutatedPromptResponse

logger = logging.getLogger("EngineV4_Step10_Elitism")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception), reraise=True)
async def _mutate_single_challenger(champion_text: str, i: int, next_gen_num: int, llm_client) -> PromptMutation:
    try:
        response = await llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL,
            response_model=MutatedPromptResponse,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a master genetic mutation algorithm. You will receive a 'Champion Prompt'. Your task is to apply a slight semantic perturbation to its structure, vocabulary, or constraints while strictly maintaining its core objective. Return ONLY the new mutated text."
                },
                {"role": "user", "content": f"Champion Prompt:\n\n{champion_text}"}
            ],
            temperature=0.8
        )
        mutated_string = response.mutated_text
    except ValidationError as ve:
        logger.error(f"Validation error in mutation {i}: {ve}")
        raise ve
    except Exception as e:
        logger.error(f"Mutation {i} failed: {e}")
        mutated_string = champion_text
        
    return PromptMutation(
        id=f"mut_v4_gen{next_gen_num}_{i}_{uuid.uuid4().hex[:4]}",
        typology_persona=f"Challenger Variant {i}",
        prompt_text=mutated_string,
        generation_num=next_gen_num
    )

async def execute_elitism_loop_v4(champion: SuperPrompt, next_gen_num: int, llm_client=None) -> List[PromptMutation]:
    """Step 10 (Engine v4): Elitism Loop. Concurrently mutates 4 challengers."""
    logger.info(f"Executing Elitism Loop for Generation {next_gen_num}...")
    mutations: List[PromptMutation] = []
    
    # Carry over reigning champion
    mutations.append(PromptMutation(
        id=f"mut_v4_gen{next_gen_num}_champion_{uuid.uuid4().hex[:4]}",
        typology_persona="Reigning Champion (Elitism)",
        prompt_text=champion.final_prompt_text,
        generation_num=next_gen_num
    ))

    async def safe_mutate(champion_text: str, i: int, next_gen_num: int, llm_client) -> PromptMutation:
        try:
            return await _mutate_single_challenger(champion_text, i, next_gen_num, llm_client)
        except Exception as e:
            logger.error(f"Mutation {i} entirely failed after retries: {e}. Falling back to champion text.")
            return PromptMutation(
                id=f"mut_v4_gen{next_gen_num}_{i}_{uuid.uuid4().hex[:4]}",
                typology_persona=f"Challenger Variant {i} (Fallback)",
                prompt_text=champion_text,
                generation_num=next_gen_num
            )

    if llm_client:
        tasks = [
            safe_mutate(champion.final_prompt_text, i, next_gen_num, llm_client)
            for i in range(1, 5)
        ]
        challengers = await asyncio.gather(*tasks)
        mutations.extend(challengers)
    else:
        for i in range(1, 5):
            mutations.append(PromptMutation(
                id=f"mut_v4_gen{next_gen_num}_{i}_{uuid.uuid4().hex[:4]}",
                typology_persona=f"Challenger Variant {i}",
                prompt_text=champion.final_prompt_text,
                generation_num=next_gen_num
            ))
            
    return mutations
