import logging
from src.engine.golden_dataset_generator.schemas import KDAMatrix, GenerationState

logger = logging.getLogger("EngineV3_Step11_EarlyStop")

def check_convergence_v3(kda: KDAMatrix, state: GenerationState) -> bool:
    """Step 11: Early Stopping & Plateau Detection."""
    if not kda.evaluations:
        return False
        
    current_best_delta = min(e.overall_delta for e in kda.evaluations)
    
    # Threshold 1: Near Perfect Delta (< 0.15)
    if current_best_delta < 0.15:
        logger.info(f"Target Delta minimized perfectly ({current_best_delta:.4f} < 0.15). Triggering early exit.")
        state.is_converged = True
        return True

    # Threshold 2: Plateau Detection over successive generations
    if state.reigning_champion:
        prev_delta = state.reigning_champion.elo_delta
        delta_improvement = prev_delta - current_best_delta
        
        if delta_improvement < 0.20:
            state.plateau_counter += 1
            logger.info(f"Plateau detected (delta gain {delta_improvement:.3f} < threshold 0.20 for {state.plateau_counter} consecutive generations).")
        else:
            state.plateau_counter = 0

        if state.plateau_counter >= 3:
            logger.info(f"Early stopping triggered at generation {state.current_generation}. Best delta: {current_best_delta:.2f}")
            state.is_converged = True
            return True

    return False
