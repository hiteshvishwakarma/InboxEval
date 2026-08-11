import pytest
from unittest.mock import AsyncMock
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_05_batch_genesis import generate_batch_genesis_mutations
from src.engine_v4.golden_dataset_generator_v4.schemas import PersonaProfileV4, SingleGenesisPrompt
from src.engine.golden_dataset_generator.schemas import HumanEmail

@pytest.mark.asyncio
async def test_prefix_cache_is_static():
    mock_client = AsyncMock()
    
    def mock_create(*args, **kwargs):
        return SingleGenesisPrompt(p_strategy="S1", action_command="Write", context_details="Context")
    mock_client.chat.completions.create.side_effect = mock_create
    
    email_angry = HumanEmail(id="1", raw_text="Angry text", clean_text="", category="")
    persona_angry = PersonaProfileV4(
        intent="Angry Intent", sentiment="Angry", nlp_task="Zero-Shot Drafting",
        domain="A", format="A", power_dynamic="A", formality_scale="Casual",
        conciseness_tier="Standard", behavioral_quirks=["Q1"], evidence_quotes=[],
        prompting_strategies=["S1"], typology_classification="T1"
    )
    
    email_prof = HumanEmail(id="2", raw_text="Professional text", clean_text="", category="")
    persona_prof = PersonaProfileV4(
        intent="Prof Intent", sentiment="Prof", nlp_task="Data Extraction",
        domain="B", format="B", power_dynamic="B", formality_scale="Professional",
        conciseness_tier="Verbose", behavioral_quirks=["Q2"], evidence_quotes=[],
        prompting_strategies=["S2"], typology_classification="T2"
    )
    
    # Execute Genesis on Email 1 (Angry Persona)
    await generate_batch_genesis_mutations(email_angry, persona_angry, mock_client)
    
    # Execute Genesis on Email 2 (Professional Persona)
    await generate_batch_genesis_mutations(email_prof, persona_prof, mock_client)
    
    # Extract the "system" prompt (index 0) from both API calls
    sys_prompt_1 = mock_client.chat.completions.create.call_args_list[0][1]['messages'][0]['content']
    sys_prompt_2 = mock_client.chat.completions.create.call_args_list[1][1]['messages'][0]['content']
    
    # ASSERTION: The hashes must be perfectly identical for the vLLM cache to hit
    assert sys_prompt_1 == sys_prompt_2, "CRITICAL FAILURE: System prompt mutated, prefix cache busted!"
