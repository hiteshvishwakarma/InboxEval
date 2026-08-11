import pytest
import asyncio
from unittest.mock import AsyncMock
from pydantic import ValidationError
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_05_batch_genesis import generate_batch_genesis_mutations
from src.engine_v4.golden_dataset_generator_v4.schemas import PersonaProfileV4, BatchGenesisResponse, SingleGenesisPrompt
from src.engine.golden_dataset_generator.schemas import HumanEmail

@pytest.fixture
def mock_persona():
    return PersonaProfileV4(
        intent="Demand Refund", sentiment="Angry", nlp_task="Zero-Shot Drafting",
        domain="E-Commerce", format="Cold Pitch", power_dynamic="Vendor to Client", formality_scale="Casual",
        conciseness_tier="Standard", behavioral_quirks=["Passive-aggressive"], evidence_quotes=[],
        prompting_strategies=["S1", "S2", "S3", "S4", "S5"], typology_classification="T1"
    )

@pytest.fixture
def mock_email():
    return HumanEmail(id="1", raw_text="Give me my money back.", clean_text="", category="")

@pytest.mark.asyncio
async def test_genesis_happy_path(mock_persona, mock_email):
    """Positive: Asserts exactly 5 mutations are parsed correctly."""
    mock_client = AsyncMock()
    def mock_create(*args, **kwargs):
        return SingleGenesisPrompt(p_strategy="S1", action_command="Write", context_details="Context")
        
    mock_client.chat.completions.create.side_effect = mock_create
    
    mutations = await generate_batch_genesis_mutations(mock_email, mock_persona, mock_client)
    assert len(mutations) == 5
    assert mutations[0].generation_num == 0
    assert "Write" in mutations[0].prompt_text
    assert mock_client.chat.completions.create.call_count == 5

@pytest.mark.asyncio
async def test_genesis_llm_hallucination(mock_persona, mock_email):
    """Negative: Asserts that Pydantic validation errors bubble up for Tenacity."""
    mock_client = AsyncMock()
    # Simulate the LLM returning complete garbage that causes the client wrapper to raise an exception
    mock_client.chat.completions.create.side_effect = Exception("ValidationError: missing fields")
    
    with pytest.raises(Exception, match="ValidationError"):
        await generate_batch_genesis_mutations(mock_email, mock_persona, mock_client)

@pytest.mark.asyncio
async def test_genesis_anti_meta_leak(mock_persona, mock_email):
    """Security: Asserts system prompt contains the explicit anti-meta leak guard."""
    mock_client = AsyncMock()
    def mock_create(*args, **kwargs):
        return SingleGenesisPrompt(p_strategy="S1", action_command="Write", context_details="Context")
    mock_client.chat.completions.create.side_effect = mock_create
    await generate_batch_genesis_mutations(mock_email, mock_persona, mock_client)
    sys_prompt = mock_client.chat.completions.create.call_args[1]['messages'][0]['content']
    
    assert "ANTI-META LEAK" in sys_prompt

@pytest.mark.asyncio
async def test_genesis_persona_injection(mock_persona, mock_email):
    """Business: Asserts that persona variables are actively injected into the user prompt."""
    mock_client = AsyncMock()
    def mock_create(*args, **kwargs):
        return SingleGenesisPrompt(p_strategy="S1", action_command="Write", context_details="Context")
    mock_client.chat.completions.create.side_effect = mock_create
    await generate_batch_genesis_mutations(mock_email, mock_persona, mock_client)
    user_prompt = mock_client.chat.completions.create.call_args[1]['messages'][1]['content']
    
    assert "Passive-aggressive" in user_prompt
    assert "Demand Refund" in user_prompt
