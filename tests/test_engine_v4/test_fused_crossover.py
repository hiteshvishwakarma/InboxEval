import pytest
import asyncio
from unittest.mock import AsyncMock
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_08_09_fused_crossover import generate_fused_critique_and_crossover_v4
from src.engine_v4.golden_dataset_generator_v4.schemas import PersonaProfileV4
from src.engine.golden_dataset_generator.schemas import HumanEmail, KDAMatrix, EvaluatedEmail

@pytest.fixture
def mock_persona():
    return PersonaProfileV4(
        intent="Demand Refund", sentiment="Angry", nlp_task="Zero-Shot Drafting",
        domain="E-Commerce", format="Cold Pitch", power_dynamic="Vendor to Client", formality_scale="Casual",
        conciseness_tier="Standard", behavioral_quirks=["Passive-aggressive"], evidence_quotes=[],
        prompting_strategies=["S1"], typology_classification="T1"
    )

@pytest.fixture
def mock_kda(mock_evals):
    return KDAMatrix(
        generation_num=1,
        overall_winner_mutation_id="mut_1",
        best_tone_mutation_id="mut_2",
        best_conciseness_mutation_id="mut_3",
        best_accuracy_mutation_id="mut_1",
        evaluations=mock_evals
    )

@pytest.fixture
def mock_evals():
    return [
        EvaluatedEmail(mutation_id="mut_1", prompt_text="A", synthetic_text="A_syn", tone_score=0, conciseness_score=0, accuracy_score=0, tone_delta=0, conciseness_delta=0, accuracy_delta=0, persona_deviation_penalty=0, overall_delta=6.0),
        EvaluatedEmail(mutation_id="mut_2", prompt_text="B", synthetic_text="B_syn", tone_score=0, conciseness_score=0, accuracy_score=0, tone_delta=0, conciseness_delta=0, accuracy_delta=0, persona_deviation_penalty=0, overall_delta=7.0),
        EvaluatedEmail(mutation_id="mut_3", prompt_text="C", synthetic_text="C_syn", tone_score=0, conciseness_score=0, accuracy_score=0, tone_delta=0, conciseness_delta=0, accuracy_delta=0, persona_deviation_penalty=0, overall_delta=8.0)
    ]

@pytest.mark.asyncio
async def test_crossover_happy_path_and_1_call_fusion(mock_kda, mock_evals, mock_persona):
    """Positive & Performance: Mocks LLM returning critique and command in exactly 1 call."""
    mock_email = HumanEmail(id="1", raw_text="Ref text", clean_text="", category="")
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    
    mock_response.judge_critique = "Critique text"
    mock_response.action_command = "Draft"
    mock_response.context_details = "New context"
    mock_client.chat.completions.create.return_value = mock_response
    
    _, super_prompt = await generate_fused_critique_and_crossover_v4(mock_kda, mock_persona, mock_email, mock_client)
    
    assert super_prompt.final_prompt_text == "Draft New context"
    assert mock_client.chat.completions.create.call_count == 1

@pytest.mark.asyncio
async def test_crossover_anti_verbatim_and_donor_dna(mock_kda, mock_evals, mock_persona):
    """Security & Business (Bug 3): Asserts anti-meta leak guard and donor DNA injection."""
    mock_email = HumanEmail(id="1", raw_text="Ref text", clean_text="", category="")
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.judge_critique = "C"
    mock_response.action_command = "D"
    mock_response.context_details = "E"
    mock_client.chat.completions.create.return_value = mock_response
    
    await generate_fused_critique_and_crossover_v4(mock_kda, mock_persona, mock_email, mock_client)
    
    sys_prompt = mock_client.chat.completions.create.call_args[1]['messages'][0]['content']
    user_prompt = mock_client.chat.completions.create.call_args[1]['messages'][1]['content']
    
    assert "ANTI-VERBATIM COPYING GUARD" in sys_prompt
    
    # Bug 3 checks
    assert "Demand Refund" in user_prompt
    assert "Passive-aggressive" in user_prompt
    assert "DONOR DNA" in user_prompt
