import logging
from typing import List
from ..schemas import EvaluatedEmail, KDAMatrix

logger = logging.getLogger("Step07_KDARanking")

def calculate_kda_ranking(evaluations: List[EvaluatedEmail], generation_num: int) -> KDAMatrix:
    """
    Step 7: KDA Matrix & N-Way Ranking.
    Determines the overall winner based on lowest overall_delta.
    Extracts individual parameter winners to 'rescue' good DNA from losing prompts.
    """
    if not evaluations:
        raise RuntimeError("Cannot generate KDA Matrix from empty evaluation list.")

    logger.info(f"Calculating KDA Matrix for Generation {generation_num} with {len(evaluations)} evaluations...")

    # 1. Overall Ranking (Tournament Winner)
    # Sort ascending by overall_delta. [0] is the winner.
    sorted_by_overall = sorted(evaluations, key=lambda e: e.overall_delta)
    overall_winner = sorted_by_overall[0]

    # 2. The KDA Sub-Parameter Extraction (The Rescue Logic)
    # Tie-breaker logic is implicitly handled because we use sorted_by_overall as the base.
    # By using `min` with a key, Python returns the first minimum encountered.
    # Since the list is already sorted by overall_delta, ties in sub-parameters 
    # will naturally favor the mutation with the better overall_delta.
    
    best_tone = min(sorted_by_overall, key=lambda e: e.tone_delta)
    best_conciseness = min(sorted_by_overall, key=lambda e: e.conciseness_delta)
    best_accuracy = min(sorted_by_overall, key=lambda e: e.accuracy_delta)

    # 3. Final Assembly
    matrix = KDAMatrix(
        generation_num=generation_num,
        overall_winner_mutation_id=overall_winner.mutation_id,
        best_tone_mutation_id=best_tone.mutation_id,
        best_conciseness_mutation_id=best_conciseness.mutation_id,
        best_accuracy_mutation_id=best_accuracy.mutation_id,
        evaluations=sorted_by_overall  # Store the ranked list
    )
    
    logger.info(f"Generation {generation_num} Winner: {overall_winner.mutation_id} (Delta: {overall_winner.overall_delta:.2f})")
    
    return matrix
