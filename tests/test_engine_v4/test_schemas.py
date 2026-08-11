import pytest
from pydantic import ValidationError
from src.engine_v4.golden_dataset_generator_v4.schemas import PersonaProfileV4

def test_persona_schema_initialization():
    """
    Proves that the consolidated V4 schema strictly accepts all 11 axes.
    """
    valid_data = {
        "intent": "Test Intent",
        "sentiment": "Neutral",
        "nlp_task": "Zero-Shot Drafting",
        "domain": "Test Domain",
        "format": "Test Format",
        "power_dynamic": "Test Dynamic",
        "formality_scale": "Professional",
        "conciseness_tier": "Standard", # The critical 11th axis
        "behavioral_quirks": ["quirk 1"],
        "evidence_quotes": ["quote 1"],
        "prompting_strategies": ["strat 1", "strat 2"],
        "typology_classification": "Test_Typology"
    }
    
    # ASSERTION 1: Should instantiate perfectly without raising ValidationError
    persona = PersonaProfileV4(**valid_data)
    assert persona.conciseness_tier == "Standard"
    
    # ASSERTION 2: Missing the 11th axis must crash the validation
    invalid_data = valid_data.copy()
    del invalid_data["conciseness_tier"]
    
    with pytest.raises(ValidationError):
        PersonaProfileV4(**invalid_data)
