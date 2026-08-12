# Engine v4 Implementation Plan: Focus on Bug 2 (Zero Genetic Variation)

## Goal Description
You correctly pointed out that if I rushed the documentation on Bug 1, I likely missed critical nuances on the other bugs. By forcing me to focus strictly on **Bug 2** right now, you saved the engine from a massive sequential latency bottleneck.

**The Bug:** In `step_10_elitism.py`, the engine is supposed to take the reigning "Champion" prompt and spawn 4 mutated "Challenger" prompts. Instead, it literally clones the string 4 times without ever calling the LLM. 
**The Nuance I Missed Earlier:** If I just throw an LLM call inside the existing `for i in range(1, 5):` loop, it will execute *sequentially*. That would force the engine to wait for 4 sequential LLM generations, destroying our throughput. We must execute all 4 mutations concurrently using `asyncio.gather`.

## Proposed Changes

### [MODIFY] `src/engine_v4/golden_dataset_generator_v4/engine_steps/step_10_elitism.py`
We will replace the string-cloning loop with a concurrent, schema-enforced LLM mutation batch.

```python
import uuid
import logging
import asyncio
from typing import List
from pydantic import BaseModel
from src.engine.golden_dataset_generator.schemas import SuperPrompt, PromptMutation
from src.engine.golden_dataset_generator.config import config

logger = logging.getLogger("EngineV4_Step10_Elitism")

# We define a strict schema to prevent the LLM from hallucinating conversational filler
class MutatedPromptResponse(BaseModel):
    mutated_text: str

async def _mutate_single_challenger(champion_text: str, i: int, next_gen_num: int, llm_client) -> PromptMutation:
    """Helper function to run a single LLM mutation asynchronously."""
    try:
        response = await llm_client.chat.completions.acreate(
            model=config.vllm_model,
            response_model=MutatedPromptResponse,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a master genetic mutation algorithm. You will receive a 'Champion Prompt'. Your task is to apply a slight semantic perturbation to its structure, vocabulary, or constraints while strictly maintaining its core objective. Return ONLY the new mutated text."
                },
                {"role": "user", "content": f"Champion Prompt:\n\n{champion_text}"}
            ],
            temperature=0.8 # Higher temp for genetic variance
        )
        mutated_string = response.mutated_text
    except Exception as e:
        logger.error(f"Mutation {i} failed, falling back to clone: {e}")
        mutated_string = champion_text
        
    return PromptMutation(
        id=f"mut_gen{next_gen_num}_{i}_{uuid.uuid4().hex[:4]}",
        typology_persona=f"Challenger Variant {i}",
        prompt_text=mutated_string,
        generation_num=next_gen_num
    )

async def execute_elitism_loop_v4(champion: SuperPrompt, next_gen_num: int, llm_client=None) -> List[PromptMutation]:
    """Step 10: Elitism Loop. Carries over reigning champion and concurrently mutates 4 new challengers."""
    logger.info(f"Executing Elitism Loop for Generation {next_gen_num}...")
    mutations: List[PromptMutation] = []
    
    # 1. Elitism: Carry over reigning champion unmodified as Mutation 0
    mutations.append(PromptMutation(
        id=f"mut_gen{next_gen_num}_champion_{uuid.uuid4().hex[:4]}",
        typology_persona="Reigning Champion (Elitism)",
        prompt_text=champion.final_prompt_text,
        generation_num=next_gen_num
    ))

    # 2. Concurrently derive 4 mutated variants from the champion prompt text
    tasks = [
        _mutate_single_challenger(champion.final_prompt_text, i, next_gen_num, llm_client)
        for i in range(1, 5)
    ]
    
    challengers = await asyncio.gather(*tasks)
    mutations.extend(challengers)
        
    return mutations
```

## Verification Plan (The Pytest)
We will write a test that mathematically proves that `asyncio.gather` fires exactly 4 concurrent LLM calls.

### [NEW] `tests/test_engine_v4/test_elitism.py`
```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_10_elitism import execute_elitism_loop_v4, MutatedPromptResponse
from src.engine.golden_dataset_generator.schemas import SuperPrompt

@pytest.mark.asyncio
async def test_elitism_mutates_concurrently():
    mock_client = AsyncMock()
    # Mock the instructor Pydantic response
    mock_client.chat.completions.acreate.return_value = MutatedPromptResponse(mutated_text="I am a mutated prompt")
    
    mock_champion = SuperPrompt(id="champ_1", final_prompt_text="I am the champion")
    
    # Execute the loop
    results = await execute_elitism_loop_v4(mock_champion, 2, mock_client)
    
    # ASSERTIONS:
    # 1. Total array size must be 5 (1 champion + 4 challengers)
    assert len(results) == 5
    
    # 2. The champion must be carried over exactly
    assert results[0].prompt_text == "I am the champion"
    
    # 3. The LLM must have been called exactly 4 times
    assert mock_client.chat.completions.acreate.call_count == 4
    
    # 4. The challengers must contain the mutated text
    for i in range(1, 5):
        assert results[i].prompt_text == "I am a mutated prompt"
```
