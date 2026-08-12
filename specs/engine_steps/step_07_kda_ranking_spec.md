# Technical Spec: Step 07 - KDA Matrix & N-Way Ranking

## Objective
This module ingests the 5 evaluated mutations and determines the winners. It executes the mathematical correction defined in the architecture: it does NOT rank based on absolute score, but strictly on Delta Minimization. It identifies the overall Champion, but also rescues sub-traits from losing mutations by finding the individual parameter winners.

## I/O Signatures
*   **Input Data:** 
    *   `evaluations`: `List[EvaluatedEmail]` (The 5 generated emails and their deltas)
    *   `generation_num`: `int`
*   **Output Data:** `KDAMatrix`

## Core Logic Workflow

### 1. Overall Ranking (Tournament Winner)
*   Sort the `evaluations` list in ascending order based on `overall_delta` (Lower is better).
*   The `EvaluatedEmail` at index `[0]` is the tournament winner.
*   Extract its `mutation_id` as `overall_winner_mutation_id`.

### 2. The KDA Sub-Parameter Extraction (The Rescue Logic)
Even if a prompt lost the overall tournament, it might have achieved the perfect Tone. We must rescue that DNA for the Step 9 Genetic Crossover.
*   **Tone Winner:** Search the list for the `EvaluatedEmail` with the absolute lowest `tone_delta`. Extract its `mutation_id` as `best_tone_mutation_id`.
*   **Conciseness Winner:** Search the list for the `EvaluatedEmail` with the absolute lowest `conciseness_delta`. Extract its `mutation_id` as `best_conciseness_mutation_id`.
*   **Accuracy Winner:** Search the list for the `EvaluatedEmail` with the absolute lowest `accuracy_delta`. Extract its `mutation_id` as `best_accuracy_mutation_id`.

### 3. Final Assembly
Compile the extracted IDs and the raw list of `evaluations` into the `KDAMatrix` Pydantic model. Return the matrix.

## Edge Cases & Error Handling
*   **Tie-Breakers:** If two mutations have the exact same delta (e.g., both achieved a `0.0` tone delta), the system defaults to the mutation that had the lower `overall_delta` to resolve the tie.
*   **Failed Batch:** If the list of `evaluations` is empty (due to an upstream catastrophic failure), raise a `RuntimeError("Cannot generate KDA Matrix from empty evaluation list.")`.
