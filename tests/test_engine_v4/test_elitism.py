import pytest
import asyncio
from unittest.mock import AsyncMock
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_10_elitism import execute_elitism_loop_v4
from src.engine.golden_dataset_generator.schemas import SuperPrompt

@pytest.fixture
def mock_champion():
    return SuperPrompt(
        id="champ_1",
        base_mutation_id="mut_1",
        injected_traits={},
        elo_delta=0.0,
        final_prompt_text="You are a perfect champion prompt."
    )

@pytest.mark.asyncio
async def test_elitism_creates_5_mutants_concurrently(mock_champion):
    """Positive, Business & Performance (Bug 2): Creates exactly 5 mutations using asyncio.gather."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    
    mock_response.mutated_text = "Mutated variant."
    mock_client.chat.completions.create.return_value = mock_response
    
    mutations = await execute_elitism_loop_v4(mock_champion, 2, mock_client)
    
    assert len(mutations) == 5
    # The champion is carried over directly (1 variant), so 4 LLM calls should be made concurrently
    assert mock_client.chat.completions.create.call_count == 4
    
    for m in mutations:
        assert m.generation_num == 2

@pytest.mark.asyncio
async def test_elitism_champion_protection(mock_champion):
    """Security: Asserts that mutations[0] is an unmodified clone of the champion."""
    mock_client = AsyncMock()
    # Mocking the nested mutated_text property
    mock_response = AsyncMock()
    mock_response.mutated_text = "Mutated variant."
    mock_client.chat.completions.create.return_value = mock_response
    
    mutations = await execute_elitism_loop_v4(mock_champion, 2, mock_client)
    
    assert mutations[0].prompt_text == "You are a perfect champion prompt."
    assert "Reigning Champion" in mutations[0].typology_persona

@pytest.mark.asyncio
async def test_elitism_llm_crash_fallback(mock_champion):
    """Negative: Asserts that an LLM crash gracefully falls back to cloning the champion."""
    mock_client = AsyncMock()
    # Force a failure on all LLM calls
    mock_client.chat.completions.create.side_effect = Exception("API Timeout")
    
    mutations = await execute_elitism_loop_v4(mock_champion, 2, mock_client)
    
    # It should still return 5 mutations, but the variants will just be clones of the champion text
    assert len(mutations) == 5
    for i in range(1, 5):
        assert mutations[i].prompt_text == "You are a perfect champion prompt."
