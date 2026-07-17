# Technical Spec: Step 01 - Raw Ingestion

## Objective
This is the entry node for the entire Golden Dataset Generator. It acts as a strict typing boundary, preventing malformed, raw, or unsanitized data from contaminating the engine. It takes a raw string (the target human email) and standardizes it into the `HumanEmail` schema.

## I/O Signatures
*   **Input Data:** 
    *   `raw_text`: `str` (The raw text of the target human email)
    *   `metadata`: `Dict[str, Any]` (Optional JSON metadata like date, sender, industry)
*   **Output Data:** `HumanEmail` (Strict Pydantic Model)

## Core Logic Workflow

### 1. Validation & Sanitization
*   Verify that `raw_text` is not null or an empty string. If empty, raise a `ValueError`.
*   Strip leading/trailing whitespace from the text.

### 2. Schema Binding
*   Generate a unique `uuid4` string for the email ID.
*   Instantiate the `HumanEmail` Pydantic model.
    *   `id`: `generated_uuid`
    *   `raw_text`: `sanitized_text`
    *   `metadata`: `metadata` (defaults to `{}` if none provided).

### 3. Return
*   Return the validated `HumanEmail` object to the Orchestrator to be passed to Step 2.

## Edge Cases & Error Handling
*   **Empty Text:** If `raw_text` is empty after stripping, raise `ValueError("Cannot ingest empty email text.")`.
*   **Type Coercion:** If `metadata` is passed as a string (e.g., from a CSV parser), attempt to `json.loads()` it into a Dictionary before schema binding, or reject it if invalid.
