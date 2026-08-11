import logging
from typing import List
from src.engine.golden_dataset_generator.schemas import EvaluatedEmail, KDAMatrix

logger = logging.getLogger("EngineV4_Step07_KDARanking")

def calculate_kda_ranking_v4(evaluations: List[EvaluatedEmail], gen_num: int) -> KDAMatrix:
    """Step 07: Deterministic KDA Matrix Ranking (0 LLM calls)."""
    if not evaluations:
        raise ValueError("Cannot calculate KDA ranking: Empty evaluations list.")
        
    overall_winner = min(evaluations, key=lambda e: e.overall_delta)
    best_tone = min(evaluations, key=lambda e: e.tone_delta)
    best_conciseness = min(evaluations, key=lambda e: e.conciseness_delta)
    best_accuracy = min(evaluations, key=lambda e: e.accuracy_delta)
    
    return KDAMatrix(
        generation_num=gen_num,
        overall_winner_mutation_id=overall_winner.mutation_id,
        best_tone_mutation_id=best_tone.mutation_id,
        best_conciseness_mutation_id=best_conciseness.mutation_id,
        best_accuracy_mutation_id=best_accuracy.mutation_id,
        evaluations=evaluations
    )
