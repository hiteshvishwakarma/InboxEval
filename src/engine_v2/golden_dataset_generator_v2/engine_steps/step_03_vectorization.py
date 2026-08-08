from src.engine.golden_dataset_generator.schemas import HumanEmail, DPBCThresholds
from ..schemas import PersonaProfileV2

def get_dpbc_thresholds_v2(persona: PersonaProfileV2, email: HumanEmail, vector_db_client=None, llm_client=None) -> DPBCThresholds:
    """Step 03: KNN Vectorization & Target DPBC Threshold Derivation."""
    formality_map = {
        'Hyper-Casual': 1.0,
        'Casual': 3.0,
        'Semi-Professional': 5.0,
        'Professional': 8.0,
        'Hyper-Formal': 10.0
    }
    tone_target = formality_map.get(persona.formality_scale, 5.0)
    
    # Calculate word count for conciseness target
    words = len(email.raw_text.split())
    if words < 30:
        conciseness_target = 9.0
    elif words < 100:
        conciseness_target = 7.0
    elif words < 250:
        conciseness_target = 5.0
    else:
        conciseness_target = 3.0
        
    accuracy_target = 9.5
    
    return DPBCThresholds(
        tone_target=tone_target,
        conciseness_target=conciseness_target,
        accuracy_target=accuracy_target
    )
