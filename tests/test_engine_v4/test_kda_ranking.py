import pytest
from src.engine_v4.golden_dataset_generator_v4.engine_steps.step_07_kda_ranking import calculate_kda_ranking_v4
from src.engine.golden_dataset_generator.schemas import EvaluatedEmail

@pytest.fixture
def mock_evaluations():
    return [
        EvaluatedEmail(
            mutation_id="mut_bad", prompt_text="A", synthetic_text="A", 
            tone_score=0.0, conciseness_score=0.0, accuracy_score=0.0,
            tone_delta=5.0, conciseness_delta=5.0, accuracy_delta=5.0, persona_deviation_penalty=0.0, overall_delta=15.0
        ),
        EvaluatedEmail(
            mutation_id="mut_best_tone", prompt_text="B", synthetic_text="B", 
            tone_score=0.0, conciseness_score=0.0, accuracy_score=0.0,
            tone_delta=1.0, conciseness_delta=8.0, accuracy_delta=8.0, persona_deviation_penalty=0.0, overall_delta=17.0
        ),
        EvaluatedEmail(
            mutation_id="mut_best_overall", prompt_text="C", synthetic_text="C", 
            tone_score=0.0, conciseness_score=0.0, accuracy_score=0.0,
            tone_delta=2.0, conciseness_delta=2.0, accuracy_delta=2.0, persona_deviation_penalty=0.0, overall_delta=6.0
        )
    ]

def test_kda_finds_winners(mock_evaluations):
    """Positive: Asserts KDA correctly identifies the lowest delta IDs."""
    kda = calculate_kda_ranking_v4(mock_evaluations, 1)
    
    assert kda.overall_winner_mutation_id == "mut_best_overall"
    assert kda.best_tone_mutation_id == "mut_best_tone"

def test_kda_empty_evaluations():
    """Negative: Asserts an empty evaluation list triggers a ValueError."""
    with pytest.raises(ValueError):
        calculate_kda_ranking_v4([], 1)

def test_kda_tie_breaker():
    """Business: Asserts ties are consistently resolved (first seen wins)."""
    ties = [
        EvaluatedEmail(
            mutation_id="mut_1", prompt_text="A", synthetic_text="A", 
            tone_score=0, conciseness_score=0, accuracy_score=0,
            tone_delta=0.0, conciseness_delta=0.0, accuracy_delta=0.0, persona_deviation_penalty=0.0, overall_delta=0.0
        ),
        EvaluatedEmail(
            mutation_id="mut_2", prompt_text="B", synthetic_text="B", 
            tone_score=0, conciseness_score=0, accuracy_score=0,
            tone_delta=0.0, conciseness_delta=0.0, accuracy_delta=0.0, persona_deviation_penalty=0.0, overall_delta=0.0
        )
    ]
    
    kda = calculate_kda_ranking_v4(ties, 1)
    assert kda.overall_winner_mutation_id == "mut_1"
