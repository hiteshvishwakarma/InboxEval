# Technical Spec: Step 11 - Early Stopping & Plateau Detection

## Objective
This module acts as the financial and computational circuit breaker for the Genetic Algorithm. Instead of blindly running all 10 generations, it mathematically analyzes the `overall_delta` of the current generation's Champion. It halts the loop if the prompt has achieved perfect semantic mirroring (Convergence), or if the algorithm has stalled out and is wasting API tokens (Plateauing).

## I/O Signatures
*   **Input Data:** 
    *   `kda`: `KDAMatrix` (Provides access to the current generation's winner)
    *   `state`: `GenerationState` (The telemetry tracker holding plateau counters and past champion data)
*   **Output Data:** `bool` (True if the loop should break, False if evolution should continue)

## Core Logic Workflow

### 1. Extract Current Delta
Retrieve the `overall_winner_mutation_id` from the `kda` matrix. 
Find the corresponding `EvaluatedEmail` and extract its `overall_delta`.

### 2. Condition A: Perfect Convergence
Define a strict convergence threshold (e.g., `CONVERGENCE_THRESHOLD = 0.05`).
*   **Logic:** If `overall_delta <= CONVERGENCE_THRESHOLD`:
*   **Action:** 
    *   Set `state.is_converged = True`.
    *   Return `True`. (The AI has mathematically matched the human original).

### 3. Condition B: Plateau Detection (Generational Stagnation)
If the prompt has not perfectly converged, we must check if the Genetic Algorithm is stuck in a local minima.
*   **Check Past History:** Look at `state.reigning_champion.elo_delta` (the best score from the *previous* generation).
*   **Stagnation Check:** 
    *   If the current generation's `overall_delta` is `==` to the previous generation's delta (meaning none of the 4 Challengers managed to beat the Elitism Champion):
        *   Increment `state.plateau_counter += 1`.
    *   If the current generation's `overall_delta` is `<` the previous generation (The GA successfully bred a better prompt):
        *   Reset `state.plateau_counter = 0`.

### 4. Circuit Breaker Execution
Define a max plateau limit (e.g., `MAX_PLATEAUS = 2`).
*   **Logic:** If `state.plateau_counter >= MAX_PLATEAUS`:
*   **Action:**
    *   Set `state.is_converged = True`. (We mark it as 'converged' to cleanly break the loop, acknowledging this is the best possible prompt the engine can generate).
    *   Return `True`.
*   **Otherwise:** Return `False` (Continue the loop).

## Edge Cases & Error Handling
*   **Generation 0 (Genesis):** During the very first run (Generation 0), `state.reigning_champion` will be `None`. The Plateau Check must gracefully bypass this and not increment the counter, as there is no historical baseline to compare against yet.
