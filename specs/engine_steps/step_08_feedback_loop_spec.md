# Technical Spec: Step 08 - Closed Feedback Loop

## Objective
This module acts as the analytical bridge before the Genetic Algorithm mutates the next generation. It forces an LLM to explicitly write out the rationale for *why* the current Generation's reigning Champion failed to perfectly hit the DPBC thresholds. This explicit chain-of-thought dramatically improves the accuracy of the subsequent crossover.

## I/O Signatures
*   **Input Data:** 
    *   `kda`: `KDAMatrix` (Provides access to the winning emails)
    *   `human_email`: `HumanEmail` (The target original text)
    *   `dpbc`: `DPBCThresholds` (The mathematical goals)
    *   `llm_client`: The LLM execution client
*   **Output Data:** `JudgeFeedback`

## Core Logic Workflow

### 1. Extract the Target for Critique
Extract the `overall_winner_mutation_id` from the `kda` matrix. 
Find the corresponding `EvaluatedEmail` from the `kda.evaluations` list to get its `synthetic_text` and its `overall_delta`.

### 2. The Feedback Prompt
Pass the data to the LLM to generate the critique.
*   **Prompt Directive:** 
    ```text
    You are the Head Linguistic Judge. 
    Compare the Original Human Email to the Synthetic Generation.
    
    Original Email: {human_email.raw_text}
    Synthetic Email: {winner.synthetic_text}
    
    The Synthetic Email achieved an error delta of {winner.overall_delta}.
    Identify exactly why it failed to achieve a perfect 0.0 Delta. 
    Analyze its Tone, Conciseness, and Factual Accuracy. Be brutally honest.
    ```
*   **Response Schema:** For now, the LLM will return a pure text string containing its analysis.

### 3. Assembly
Wrap the `feedback_text` and the `kda_matrix_id` (a generated ID or string representation of the generation number) into the `JudgeFeedback` Pydantic model.

## Edge Cases & Error Handling
*   **Missing Winner:** If the KDA Matrix somehow contains an empty `evaluations` list, raise a `ValueError`.
*   **Perfect Convergence:** If the `overall_winner` achieved an `overall_delta` of `< 0.05` (or whatever our convergence threshold is), the feedback loop should bypass the LLM and return a hardcoded success message: `"Delta minimized. Prompt has converged perfectly."` This saves API costs.
