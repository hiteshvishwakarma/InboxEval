import pytest
import asyncio
from unittest.mock import AsyncMock
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_06_static_evaluator import evaluate_mutations_v4
from src.engine_v4.golden_dataset_generator_v4.schemas import SingleCandidateScore
from src.engine.golden_dataset_generator.schemas import HumanEmail, DPBCThresholds, PromptMutation

@pytest.fixture
def mock_mutations():
    return [PromptMutation(id=f"mut_{i}", typology_persona="T", prompt_text="P", generation_num=0) for i in range(5)]

@pytest.fixture
def mock_email():
    return HumanEmail(id="1", raw_text="Ref text", clean_text="", category="")

@pytest.fixture
def mock_dpbc():
    return DPBCThresholds(tone_target=5.0, conciseness_target=5.0, accuracy_target=5.0)

@pytest.mark.asyncio
async def test_evaluator_valid_scores_and_batching(mock_mutations, mock_email, mock_dpbc):
    """Positive & Performance: Evaluates 5 variants using 5 concurrent un-batched LLM calls."""
    mock_client = AsyncMock()
    
    def mock_create(*args, **kwargs):
        import re
        messages = kwargs.get('messages', [])
        content = messages[1]['content']
        match = re.search(r"ID: (mut_\d+)", content)
        m_id = match.group(1) if match else "mut_unknown"
        return SingleCandidateScore(
            mutation_id=m_id, synthetic_text="Syn", tone_score=5.0, 
            conciseness_score=5.0, accuracy_score=5.0, persona_penalty=0.0
        )
        
    mock_client.chat.completions.create.side_effect = mock_create
    
    evals = await evaluate_mutations_v4(mock_mutations, mock_email, mock_dpbc, mock_client)
    
    assert len(evals) == 5
    # Batching check: Should be 5 concurrent calls now!
    assert mock_client.chat.completions.create.call_count == 5

@pytest.mark.asyncio
async def test_evaluator_missing_fields_bubble_up(mock_mutations, mock_email, mock_dpbc):
    """Negative: Asserts silent failure block is removed, forcing Tenacity to retry."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("ValidationError: missing tone_score")
    
    with pytest.raises(Exception, match="ValidationError"):
        await evaluate_mutations_v4(mock_mutations, mock_email, mock_dpbc, mock_client)

@pytest.mark.asyncio
async def test_evaluator_delta_math(mock_mutations, mock_email):
    """Business: Mathematically proves the delta equation works correctly."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    
    # DPBC Targets are all 5.0
    dpbc_target = DPBCThresholds(tone_target=5.0, conciseness_target=5.0, accuracy_target=5.0)
    
    mock_client.chat.completions.create.return_value = SingleCandidateScore(
        mutation_id="mut_0", synthetic_text="Syn", tone_score=8.0, 
        conciseness_score=2.0, accuracy_score=5.0, persona_penalty=0.0
    )
    
    evals = await evaluate_mutations_v4([mock_mutations[0]], mock_email, dpbc_target, mock_client)
    
    # |5.0 - 8.0| = 3.0
    assert evals[0].tone_delta == 3.0
    # |5.0 - 2.0| = 3.0
    assert evals[0].conciseness_delta == 3.0
    assert evals[0].accuracy_delta == 0.0
    assert evals[0].overall_delta == 6.0
