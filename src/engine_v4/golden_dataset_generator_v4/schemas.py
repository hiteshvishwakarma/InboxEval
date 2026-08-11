from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Re-use core data models from engine baseline
from src.engine.golden_dataset_generator.schemas import (
    RawEmailRecord, GoldenDatasetRecord, HumanEmail, DPBCThresholds,
    EvaluatedEmail, KDAMatrix, GenerationState
)

class PersonaProfileV4(BaseModel):
    """Phase 1: Full 11-Axis Persona Profile computed horizontally offline."""
    intent: str = Field(..., description="Primary goal of the email (e.g., 'Demand Refund')")
    sentiment: str = Field(..., description="Emotional state (e.g., 'Angry', 'Urgent')")
    
    # Core Classification Axes
    nlp_task: Literal['Zero-Shot Drafting', 'Data Extraction', 'Thread Summarization', 'Tone Translation'] = Field(..., description="Must be exactly one of the 4 valid NLP tasks.")
    domain: str = Field(..., description="Industry or topic (e.g., 'SaaS Patch Notes', 'E-Commerce Refunds')")
    format: str = Field(..., description="Physical layout (e.g., 'Cold Pitch', 'System Alert')")
    
    # Behavioral & Stylistic Axes
    power_dynamic: str = Field(..., description="Relationship dynamic (e.g., 'Vendor to Client')")
    formality_scale: Literal['Hyper-Casual', 'Casual', 'Semi-Professional', 'Professional', 'Hyper-Formal'] = Field(..., description="Strict formality scale rating.")
    conciseness_tier: Literal['Hyper-Brief', 'Standard', 'Verbose', 'Rambling'] = Field(..., description="Target length/verbosity tier.")
    
    # Evidence & Injection Traits
    behavioral_quirks: List[str] = Field(..., description="List of specific traits (e.g., 'Passive-aggressive')")
    evidence_quotes: List[str] = Field(..., description="Verbatim substring quotes from raw email proving behavioral quirks.")
    prompting_strategies: List[str] = Field(..., description="5 pre-cached prompting strategies.")
    typology_classification: str = Field(..., description="Overall Persona tag (e.g., 'B2B_Hardware_Angry_Support')")

class SingleGenesisPrompt(BaseModel):
    p_strategy: str = Field(..., description="Prompting strategy used.")
    action_command: str = Field(..., description="Instruction verb: Write/Draft/Generate/etc.")
    context_details: str = Field(..., description="Authentic context details.")

class BatchGenesisResponse(BaseModel):
    """Step 05: Consolidated 1-call Genesis candidate generation."""
    mutations: List[SingleGenesisPrompt] = Field(..., description="List of 5 generated base prompt mutations.")

class FusedCritiqueAndCrossoverResponse(BaseModel):
    """Step 08/09: Fused Critique and Polygenic Crossover in 1 single LLM call."""
    judge_critique: str = Field(..., description="Part 1: Critique explaining Tone, Conciseness, and Accuracy gaps.")
    action_command: str = Field(..., description="Part 2: Action command starting with Write/Draft/Generate/etc.")
    context_details: str = Field(..., description="Part 2: Synthesized super prompt context merging donor DNA.")

class SingleCandidateScore(BaseModel):
    mutation_id: str = Field(..., description="ID of candidate mutation evaluated.")
    synthetic_text: str = Field(..., description="Generated email text.")
    tone_score: float = Field(..., description="Absolute Tone Score (0.0 to 10.0)")
    conciseness_score: float = Field(..., description="Absolute Conciseness Score (0.0 to 10.0)")
    accuracy_score: float = Field(..., description="Absolute Accuracy Score (0.0 to 10.0)")
    persona_penalty: float = Field(0.0, description="Penalty applied if persona structure is violated.")

class BatchEvaluationResponse(BaseModel):
    """Step 06: Consolidated single-call Dual-Scoring response for 5 candidates."""
    evaluations: List[SingleCandidateScore] = Field(..., description="Evaluations for all 5 candidates.")

class MutatedPromptResponse(BaseModel):
    """Step 10: The mutated prompt text from the Elitism step."""
    mutated_text: str = Field(..., description="The finalized mutated prompt string.")
