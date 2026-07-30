import logging
from ..schemas import KDAMatrix, GenerationState
from ..config import config

logger = logging.getLogger("Step11_EarlyStopping")

def check_convergence(kda: KDAMatrix, state: GenerationState, convergence_threshold: float = 0.05, max_plateaus: int = config.EARLY_STOP_PLATEAU_LIMIT) -> bool:
    """
    Step 11: Early Stopping & Plateau Detection.
    Circuit breaker for the evolutionary loop. Returns True if the algorithm 
    has converged on a perfect delta, or if it has plateaued for N generations.
    """
    logger.info(f"Executing Early Stop checks for Generation {kda.generation_num}...")
    
    # 1. Extract Current Delta
    # Since kda.evaluations is sorted in Step 7, index 0 is the overall winner.
    winner_eval = next(e for e in kda.evaluations if e.mutation_id == kda.overall_winner_mutation_id)
    current_delta = winner_eval.overall_delta
    
    # 2. Condition A: Perfect Convergence
    if current_delta <= convergence_threshold:
        logger.info(f"CONVERGENCE ACHIEVED: Delta {current_delta:.3f} is below threshold {convergence_threshold}.")
        state.is_converged = True
        return True
        
    # 3. Condition B: Plateau Detection
    # If this is Generation 0, there is no history to compare against.
    if state.reigning_champion is None:
        logger.info(f"Generation {kda.generation_num}: No historical baseline to check for plateau.")
        return False
        
    previous_delta = state.reigning_champion.elo_delta
    
    # Check for stagnation or regression
    if current_delta >= previous_delta:
        state.plateau_counter += 1
        logger.warning(f"Plateau detected! Current delta ({current_delta:.3f}) failed to beat previous delta ({previous_delta:.3f}). Counter: {state.plateau_counter}/{max_plateaus}")
    else:
        # The GA successfully improved the score. Reset the counter.
        logger.info(f"Improvement detected: {current_delta:.3f} beats {previous_delta:.3f}. Resetting plateau counter.")
        state.plateau_counter = 0
        
    # 4. Circuit Breaker Execution
    if state.plateau_counter >= max_plateaus:
        logger.error(f"CIRCUIT BROKEN: Algorithm stalled for {max_plateaus} consecutive generations. Triggering Early Stop.")
        state.is_converged = True
        return True
        
    return False
