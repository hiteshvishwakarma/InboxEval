import uuid
import logging
from typing import List

from ..schemas import SuperPrompt, PromptMutation
from ..config import config

logger = logging.getLogger("Step10_Elitism")

def execute_elitism_loop(champion: SuperPrompt, next_gen_num: int, llm_client=None) -> List[PromptMutation]:
    """
    Step 10: Elitism Loop.
    Converts the SuperPrompt into the Reigning Champion for the next generation.
    Spawns 4 new variations (Challengers) to attack the Champion's delta.
    """
    logger.info(f"Executing Elitism Loop for Generation {next_gen_num}...")
    
    mutations: List[PromptMutation] = []
    
    # 1. Protect the Champion
    # We carry the exact SuperPrompt DNA over untouched.
    champion_mutation = PromptMutation(
        id=f"mut_gen{next_gen_num}_CHAMP_{uuid.uuid4().hex[:4]}",
        typology_persona="Reigning Champion (Base)",
        prompt_text=champion.final_prompt_text,
        generation_num=next_gen_num
    )
    mutations.append(champion_mutation)
    
    # 2. Spawn the Challengers
    challenger_prompt = f"""
    You are an Evolutionary Prompt Engineer.
    Here is the current Champion Prompt: 
    {champion.final_prompt_text}
    
    You must generate 4 slight variations of this prompt. Maintain its core instructions, 
    but explore different phrasing, brevity, or tone emphasis to try and improve performance. 
    Return exactly 4 distinct prompts.
    """
    from pydantic import BaseModel
    class ChallengersList(BaseModel):
        prompts: List[str]

    if llm_client:
        # In production, Instructor would force the LLM to return exactly a List[str] of size 4
        response_data = llm_client.chat.completions.create(
            model=config.DEFAULT_GENERATION_MODEL,
            response_model=ChallengersList,
            messages=[{"role": "user", "content": challenger_prompt}]
        )
        generated_texts = response_data.prompts
        
    else:
        # Mocking the 4 challenger texts
        generated_texts = [
            f"Challenger 1 Variant of {champion.id}",
            f"Challenger 2 Variant of {champion.id}",
            f"Challenger 3 Variant of {champion.id}",
            f"Challenger 4 Variant of {champion.id}"
        ]
    
    # 3. Assembly and Edge Case Safety
    for idx, text in enumerate(generated_texts[:4]): # Safely slice to ensure max 4 challengers
        challenger_mutation = PromptMutation(
            id=f"mut_gen{next_gen_num}_CHAL_{idx}_{uuid.uuid4().hex[:4]}",
            typology_persona="Challenger Variant",
            prompt_text=text,
            generation_num=next_gen_num
        )
        mutations.append(challenger_mutation)
        
    # We do not pad if the LLM hallucinated fewer than 4 challengers. 
    # A smaller, high-quality gene pool is better than generic padding.
        
    return mutations
