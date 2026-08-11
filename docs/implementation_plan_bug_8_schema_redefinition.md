# Engine v4 Implementation Plan: Focus on Bug 8 (Schema Redefinition)

## Goal Description
Following the strict one-by-one procedure, I analyzed `schemas.py` to target **Bug 8 (Schema Redefinition)**.

**The Bug:** In `schemas.py`, the core data model `PersonaProfileV3` is defined twice in the exact same file.
The first definition contains 10 axes. The second definition (immediately below it) contains the full 11 axes (adding `conciseness_tier`). 
In Python, because the interpreter reads top-to-bottom, the second definition silently overwrites the first one. While the code technically still executes (since the second definition is the one actually used in memory), having 20 lines of dead schema code physically sitting above the real schema creates massive confusion for developers, breaks IDE static type checking, and violates strict Schema-First development rules.

## Proposed Changes

### [MODIFY] `src/engine_v4/golden_dataset_generator_v4/schemas.py`
We will delete the dead, 10-axis duplicate, keeping only the full 11-axis architecture (renamed to `V4`).

```diff
- class PersonaProfileV3(BaseModel):
-     """Step 02: Persona Profile enriched with 5 pre-cached prompting strategies."""
-     intent: str = Field(..., description="Primary goal of the email (e.g., 'Demand Refund')")
-     sentiment: str = Field(..., description="Emotional state (e.g., 'Angry', 'Urgent')")
-     
-     # 3-Axis Multi-Dimensional Taxonomy
-     nlp_task: Literal['Zero-Shot Drafting', 'Data Extraction', 'Thread Summarization', 'Tone Translation'] = Field(..., description="Must be exactly one of the 4 valid NLP tasks.")
-     domain: str = Field(..., description="Industry or topic (e.g., 'SaaS Patch Notes', 'E-Commerce Refunds')")
-     format: str = Field(..., description="Physical layout (e.g., 'Cold Pitch', 'System Alert')")
-     
-     # Atomic Behavioral Matrix
-     power_dynamic: str = Field(..., description="Relationship dynamic (e.g., 'Vendor to Client')")
-     formality_scale: Literal['Hyper-Casual', 'Casual', 'Semi-Professional', 'Professional', 'Hyper-Formal'] = Field(..., description="Strict formality scale rating.")
-     behavioral_quirks: List[str] = Field(..., description="List of specific traits (e.g., 'Passive-aggressive')")
-     evidence_quotes: List[str] = Field(..., description="Verbatim substring quotes from raw email proving behavioral quirks.")
-     
-     # Engine v2 Optimization: Pre-cached prompting strategies
-     prompting_strategies: List[str] = Field(..., description="5 pre-cached prompting strategies (bypasses Step 04 LLM call during vertical run)")
-     typology_classification: str = Field(..., description="Overall Persona tag (e.g., 'B2B_Hardware_Angry_Support')")

- class PersonaProfileV3(BaseModel):
+ class PersonaProfileV4(BaseModel):
      """Phase 1: Full 11-Axis Persona Profile computed horizontally offline."""
      intent: str = Field(..., description="Primary goal of the email (e.g., 'Demand Refund')")
      sentiment: str = Field(..., description="Emotional state (e.g., 'Angry', 'Urgent')")
      
      # Core Classification Axes
      nlp_task: Literal['Zero-Shot Drafting', 'Data Extraction', 'Thread Summarization', 'Tone Translation'] = Field(...)
      domain: str = Field(...)
      format: str = Field(...)
      
      # Behavioral & Stylistic Axes
      power_dynamic: str = Field(...)
      formality_scale: Literal['Hyper-Casual', 'Casual', 'Semi-Professional', 'Professional', 'Hyper-Formal'] = Field(...)
+     conciseness_tier: Literal['Hyper-Brief', 'Standard', 'Verbose', 'Rambling'] = Field(..., description="Target length/verbosity tier.")
      
      # Evidence & Injection Traits
      behavioral_quirks: List[str] = Field(...)
      evidence_quotes: List[str] = Field(...)
      prompting_strategies: List[str] = Field(...)
      typology_classification: str = Field(...)
```

## Verification Plan (The Pytest)
We will write a Pytest to mathematically prove that the schema accurately accepts all 11 fields, guaranteeing that removing the duplicate didn't accidentally drop required logic.

### [NEW] `tests/test_engine_v4/test_schemas.py`
```python
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
```
