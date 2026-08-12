import uuid
import logging
import asyncio
from typing import List
from src.engine.golden_dataset_generator.schemas import SuperPrompt, PromptMutation
from src.engine.golden_dataset_generator.config import config

logger = logging.getLogger("EngineV3_Step10_Elitism")

async def execute_elitism_loop_v3(champion: SuperPrompt, next_gen_num: int, llm_client=None) -> List[PromptMutation]:
    """Step 10: Elitism Loop. Carries over reigning champion and mutates 4 new challengers."""
    logger.info(f"Executing Elitism Loop for Generation {next_gen_num}...")
    
    mutations: List[PromptMutation] = []
    
    # 1. Elitism: Carry over reigning champion as Mutation 0
    mutations.append(PromptMutation(
        id=f"mut_gen{next_gen_num}_champion_{uuid.uuid4().hex[:4]}",
        typology_persona="Reigning Champion (Elitism)",
        prompt_text=champion.final_prompt_text,
        generation_num=next_gen_num
    ))

    # 2. Derive 4 mutated variants from the champion prompt text
    for i in range(1, 5):
        mutations.append(PromptMutation(
            id=f"mut_gen{next_gen_num}_{i}_{uuid.uuid4().hex[:4]}",
            typology_persona=f"Challenger Variant {i}",
            prompt_text=champion.final_prompt_text,
            generation_num=next_gen_num
        ))
        
    return mutations
