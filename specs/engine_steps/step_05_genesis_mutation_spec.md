# Technical Spec: Step 05 - Genesis Mutation

## Objective
This module concludes Phase 2 (Genesis) by taking the 5 diverse Prompt Writer Personas generated in Step 4 and using them to generate 5 distinct initial prompts. These 5 prompts form Generation 0 of the evolutionary tournament. 

## I/O Signatures
*   **Input Data:** 
    *   `email`: `HumanEmail` (The target human email text)
    *   `personas`: `List[str]` (Exactly 5 persona strings from Step 4)
    *   `llm_client`: The LLM execution client
*   **Output Data:** `List[PromptMutation]` (Exactly 5 structured prompt objects)

## Core Logic Workflow

### 1. The Multi-Threaded Prompt Generation
For each of the 5 `persona` strings in the `personas` array, the system will pass the persona and the target email into the LLM.

*   **System Directive:**
    ```text
    You must adopt this persona: {persona}
    
    Your task is to write an LLM instruction prompt that, if executed, would cause an AI 
    to generate the following target email:
    "{email.raw_text}"
    
    Write ONLY the prompt itself. Do not include introductory text.
    ```

### 2. Schema Binding
The resulting prompt text for each persona is packaged into the `PromptMutation` Pydantic model:
*   `id`: `uuid4` string (e.g., `gen_0_uuid`)
*   `typology_persona`: `{persona}`
*   `prompt_text`: `{generated_prompt}`
*   `generation_num`: `0` (Since this is the Genesis batch)

### 3. Collection
Return the 5 instantiated `PromptMutation` objects as an array.

## Edge Cases & Error Handling
*   **Variable Array Size Integrity:** If an LLM call fails (e.g. timeout) for a specific persona, the system must simply skip that persona and return a smaller array (e.g., 4 mutations). We do NOT inject a generic placeholder prompt, because doing so would introduce garbage DNA into the Evolutionary Algorithm that could degrade the final bred prompt. The tournament size `N` dynamically adapts to `len(mutations)`.
