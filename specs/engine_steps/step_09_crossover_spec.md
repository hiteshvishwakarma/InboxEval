# Technical Spec: Step 09 - Polygenic Crossover

## Objective
This module executes the core Genetic Algorithm logic. Instead of just mutating one winning prompt (Standard GA), it executes a **Multi-Parent (Polygenic) Crossover**. It mathematically extracts the absolute best DNA from any of the 5 prompts in the KDA matrix and synthesizes them into the ultimate "Super Prompt."

## I/O Signatures
*   **Input Data:** 
    *   `kda`: `KDAMatrix` (Contains the overall winner and the sub-trait winners)
    *   `feedback`: `JudgeFeedback` (The strict critique of why the overall winner failed)
    *   `llm_client`: The LLM execution client
*   **Output Data:** `SuperPrompt`

## Core Logic Workflow

### 1. Retrieve the Donor DNA
Iterate through `kda.evaluations` to retrieve the original prompt text of:
*   The `overall_winner_mutation_id` (This serves as the Base Structure).
*   The `best_tone_mutation_id` (The Tone Donor).
*   The `best_conciseness_mutation_id` (The Conciseness Donor).
*   The `best_accuracy_mutation_id` (The Accuracy Donor).

*(Note: Often, a prompt will be its own donor if it won multiple categories. The system handles this seamlessly).*

### 2. The Polygenic Prompt Directive
Pass all the donor DNA and the `JudgeFeedback` to the LLM.
*   **Prompt Directive:**
    ```text
    You are an Evolutionary Prompt Engineer.
    Your task is to breed a new 'Super Prompt' by combining the best traits of multiple parents, while explicitly fixing the flaws identified by the Judge.
    
    BASE STRUCTURE: {overall_winner_prompt_text}
    TONE DONOR: {tone_winner_prompt_text}
    CONCISENESS DONOR: {conciseness_winner_prompt_text}
    ACCURACY DONOR: {accuracy_winner_prompt_text}
    
    JUDGE FEEDBACK TO FIX: {feedback.feedback_text}
    
    INSTRUCTIONS: Keep the core formatting of the BASE STRUCTURE. Inject the linguistic rules from the DONORS that made them succeed in their specific categories. Apply the Judge's feedback aggressively.
    ```

### 3. Final Assembly
The LLM returns the newly synthesized prompt string. We wrap this into the `SuperPrompt` Pydantic model.
*   `id` = Generated UUID (e.g., `Super_P_Gen_1...`)
*   `base_mutation_id` = `kda.overall_winner_mutation_id`
*   `injected_traits` = A dictionary mapping the parameters to the donor IDs (e.g., `{"tone": "mut_abc", "conciseness": "mut_xyz"}`).
*   `elo_delta` = Maps to the `overall_winner`'s delta (until it competes in the next generation).
*   `is_champion` = `True`

## Edge Cases & Error Handling
*   **Convergence Bypass:** If `feedback.feedback_text` indicates perfect convergence ("Delta minimized"), the crossover is bypassed. The `overall_winner`'s original prompt is instantly promoted to `SuperPrompt` status without any LLM alteration to prevent ruining the perfect DNA.
