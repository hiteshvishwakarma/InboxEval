# Technical Spec: Step 04 - Dynamic Persona Synthesis

## Objective
This module initiates Phase 2 (Genesis). Instead of feeding the target email to an LLM and asking it to guess a prompt just once, we synthesize a tournament bracket of 5 highly diverse "Prompt Writer Personas." This ensures the Genetic Algorithm starts with widespread genetic diversity, avoiding local minima from the very first generation.

## I/O Signatures
*   **Input Data:** 
    *   `email`: `HumanEmail` (The target original text)
    *   `persona`: `PersonaProfile` (The extracted linguistic profile from Step 2)
    *   `llm_client`: The LLM execution client
*   **Output Data:** `List[str]` (An array of 5 strings representing the generated personas)

## Core Logic Workflow

### 1. Contextual Diversity Generation
*   Pass the `email` and the `persona` into the LLM.
*   **Prompt Directive:**
    ```text
    You are an AI Genetic Diversity Engine.
    We need to write an LLM prompt that perfectly generates an email matching this profile: {persona.typology_classification}.
    
    To ensure diversity, invent 5 radically different 'Prompt Writer Personas' who might write this prompt. 
    Examples: "The Hyper-Logical Programmer", "The Aggressive Sales Exec", "The Minimalist Designer".
    
    Return EXACTLY 5 distinct persona titles as a list of strings.
    ```

### 2. Output Formatting
*   The LLM should use structured output (Instructor) to return exactly `List[str]` with a length of 5.

## Edge Cases & Error Handling
*   **Variable Array Size Constraint:** We aim for 5 diverse personas, but if the LLM hallucinates and returns fewer (e.g., 3 or 4), the module must simply accept the smaller array rather than forcefully padding it with generic garbage. In a Genetic Algorithm, a smaller population of high-quality DNA is better than polluting the gene pool with generic fallbacks. If it returns more than 5, slice the array at 5 to cap API costs.
