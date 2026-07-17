# Technical Spec: Step 10 - Elitism Loop

## Objective
The Elitism Loop solves a major flaw in basic Genetic Algorithms: Generational Degradation (where Generation 2 accidentally mutates into something worse than Generation 1). By enforcing "Elitism," we guarantee that the reigning Champion (the `SuperPrompt` from Step 9) is carried over completely untouched into the next generation to defend its title. We then spawn 4 new mutations to challenge it.

## I/O Signatures
*   **Input Data:** 
    *   `champion`: `SuperPrompt` (The output of Step 9)
    *   `next_gen_num`: `int` (The generation index we are preparing for)
    *   `llm_client`: The LLM execution client
*   **Output Data:** `List[PromptMutation]` (Size: 5. 1 Champion + 4 Challengers)

## Core Logic Workflow

### 1. Protect the Champion
Convert the `champion: SuperPrompt` directly into a `PromptMutation` object.
*   `typology_persona`: `"Reigning Champion (Base)"`
*   `prompt_text`: `champion.final_prompt_text`
*   `generation_num`: `next_gen_num`
*   Add this immediately to our output `mutations` list.

### 2. Spawn the Challengers
The system must generate 4 new Challenger mutations that attempt to beat the Champion's Delta. We do this by applying slight, randomized stylistic mutations to the Champion's perfect DNA.

*   **Prompt Directive:**
    ```text
    You are an Evolutionary Prompt Engineer.
    Here is the current Champion Prompt: 
    {champion.final_prompt_text}
    
    You must generate 4 slight variations of this prompt. Maintain its core instructions, but explore different phrasing, brevity, or tone emphasis. 
    Return exactly 4 distinct prompts.
    ```
*(Note: In a full production implementation, we can re-use Step 4 Persona Synthesis here to give each challenger a specific new persona constraint, forcing them to attack the Champion from different angles).*

### 3. Assembly
Iterate over the 4 generated texts. Wrap each in a `PromptMutation` schema:
*   `id`: Generated UUID (e.g., `mut_gen{next_gen_num}_...`)
*   `typology_persona`: `"Challenger Variant"`
*   `prompt_text`: `<llm_generated_variation>`
*   `generation_num`: `next_gen_num`

Append the 4 Challengers to the `mutations` list (which already contains the Champion). 
Return the list of 5 `PromptMutation` objects. This list will be fed back into Step 6 by the Orchestrator loop.

## Edge Cases & Error Handling
*   **LLM Hallucination:** If the LLM returns fewer or more than 4 challengers, the system must pad or slice the array to strictly ensure the final list size is exactly 5. A tournament must always have 5 combatants.
