import logging
from ..schemas import KDAMatrix, GenerationState
from ..config import config

logger = logging.getLogger("Step11_EarlyStopping")

def check_convergence(kda: KDAMatrix, state: GenerationState, convergence_threshold: float = 1.0, min_improvement: float = 0.20, max_plateaus: int = config.EARLY_STOP_PLATEAU_LIMIT) -> bool:
    """
    Step 11: Early Stopping & Plateau Detection.
    Circuit breaker for the evolutionary loop. Returns True if the algorithm 
    has converged on a near-perfect delta (<= 1.0), or if delta improvement is < 0.20 for N generations.
    """
    logger.info(f"Executing Early Stop checks for Generation {kda.generation_num}...")
    
    # 1. Extract Current Delta
    winner_eval = next(e for e in kda.evaluations if e.mutation_id == kda.overall_winner_mutation_id)
    current_delta = winner_eval.overall_delta
    
    # 2. Condition A: Near-Perfect Convergence (Delta <= 1.0)
    if current_delta <= convergence_threshold:
        logger.info(f"CONVERGENCE ACHIEVED: Delta {current_delta:.3f} is below empirical gold threshold {convergence_threshold}.")
        state.is_converged = True
        return True
        
    # 3. Condition B: Plateau / Stagnation Detection (< 0.20 improvement)
    if state.reigning_champion is None:
        logger.info(f"Generation {kda.generation_num}: No historical baseline to check for plateau.")
        return False
        
    previous_delta = state.reigning_champion.elo_delta
    delta_gain = previous_delta - current_delta
    
    # Active improvement requires at least 0.20 delta reduction
    if delta_gain < min_improvement:
        state.plateau_counter += 1
        logger.warning(f"Stagnation detected! Gain ({delta_gain:.3f}) < min threshold ({min_improvement}). Counter: {state.plateau_counter}/{max_plateaus}")
    else:
        logger.info(f"Active improvement detected: Gain {delta_gain:.3f} >= {min_improvement}. Resetting plateau counter.")
        state.plateau_counter = 0
        
    # 4. Circuit Breaker Execution
    if state.plateau_counter >= max_plateaus:
        logger.error(f"CIRCUIT BROKEN: Algorithm stalled for {max_plateaus} consecutive generations. Triggering Early Stop.")
        state.is_converged = True
        return True
        
    return False
