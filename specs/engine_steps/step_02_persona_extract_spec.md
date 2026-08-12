# Technical Spec: Step 02 - Persona Extraction

## Objective
This module is responsible for analyzing the raw human email and extracting its core linguistic and contextual DNA. It forces the LLM to output a strictly typed JSON object containing the email's Intent, Domain, Sentiment, and an overarching Typology tag (e.g., "The Angry Executive"). This profile acts as the basis for the Vector Search in Step 3.

## I/O Signatures
*   **Input Data:** 
    *   `email`: `HumanEmail` (The validated output from Step 1)
    *   `llm_client`: The LLM execution client (using Instructor for structured output)
*   **Output Data:** `PersonaProfile`

## Core Logic Workflow

### 1. The Extraction Prompt
Pass `email.raw_text` to the LLM.
*   **Prompt Directive:**
    ```text
    You are an expert linguistic profiler.
    Analyze the following human-written email:
    "{email.raw_text}"
    
    Extract the following metadata precisely:
    1. Intent: What is the core goal of the sender?
    2. Domain: What industry or context does this belong to?
    3. Sentiment: What is the emotional tone?
    4. Typology Tag: A 3-4 word overarching persona (e.g., "Frustrated B2B Client", "Concise Tech Lead").
    ```

### 2. Structured Schema Enforcement
The LLM response MUST strictly map to the `PersonaProfile` Pydantic model:
```python
class PersonaProfile(BaseModel):
    intent: str
    domain: str
    sentiment: str
    typology_classification: str
```

### 3. Assembly
*   Return the populated `PersonaProfile`.

## Edge Cases & Error Handling
*   **LLM JSON Hallucination:** If the LLM fails to return valid Pydantic JSON after 3 retries (via Instructor's built-in retry mechanics), the module must raise a `RuntimeError` rather than passing a malformed string downstream.
*   **Missing Fields:** If the LLM returns partial data (e.g., missing the `typology_tag`), it will be caught by Pydantic validation and trigger the retry loop.
