# Technical Spec: Step 06 - Forward Generation & Dual-Scoring Evaluator

## Objective
This module takes the 5 prompt mutations, generates the synthetic emails, and executes a rigorous "Dual-Scoring" evaluation to measure how close the generated email is to the target human email, while simultaneously penalizing prompts that violate their assigned persona.

## I/O Signatures
*   **Input Data:** 
    *   `mutations`: `List[PromptMutation]`
    *   `human_email`: `HumanEmail` (The target)
    *   `dpbc_thresholds`: `DPBCThresholds` (The mathematical target goals)
    *   `llm_client`: The LLM execution client
*   **Output Data:** `List[EvaluatedEmail]`

## Core Logic Workflow

### 1. Forward Generation
Iterate over each `PromptMutation` in the list.
Pass `mutation.prompt_text` to the LLM to generate a string: `synthetic_text`.

### 2. The LLM-as-a-Judge Evaluation (Score A)
Use the `llm_client` (via Instructor/Pydantic) to evaluate the `synthetic_text`.
*   **Prompt Directive:** "You are an expert evaluator. Score this synthetic email out of 10.0 based on Tone, Conciseness, and Factual Accuracy compared to the original human intent."
*   **Response Schema:** 
    ```python
    class JudgeScores(BaseModel):
        tone_score: float
        conciseness_score: float
        accuracy_score: float
    ```

### 3. Delta Minimization Calculation
Calculate the absolute error (Delta) between the LLM's score and the DPBC Target.
*   `tone_delta` = `abs(dpbc_thresholds.tone_target - judge.tone_score)`
*   `conciseness_delta` = `abs(dpbc_thresholds.conciseness_target - judge.conciseness_score)`
*   `accuracy_delta` = `abs(dpbc_thresholds.accuracy_target - judge.accuracy_score)`

### 4. Persona Deviation Penalty (Score B)
This prevents the Genetic Algorithm from producing generic, robotic prompts. We evaluate the *Prompt itself*, not just the generated email.
*   **Logic:** Does `mutation.prompt_text` sound like it was written by `mutation.typology_persona`? 
*   **Execution:** A secondary fast-LLM call evaluates the prompt constraint.
*   **Penalty Math:** If the prompt violates its persona constraint (e.g., "The Furious CEO" writes a perfectly polite, 3-paragraph prompt), apply a `persona_deviation_penalty` of `+5.0` (Since lower delta is better, this massive penalty effectively kills the mutation's chance of winning).

### 5. Final Assembly
`overall_delta` = `tone_delta` + `conciseness_delta` + `accuracy_delta` + `persona_deviation_penalty`
Return the compiled `EvaluatedEmail` schema.

## Edge Cases & Error Handling
*   **LLM Hallucination/Timeout:** If the LLM fails to return valid Pydantic scores after 3 retries, assign a massive `overall_delta` (e.g., `999.0`) to that specific mutation so it automatically loses the tournament rather than crashing the entire 5-way batch.
