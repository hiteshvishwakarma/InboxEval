# Technical Spec: Step 03 - Vectorization & DPBC Thresholds

## Objective
The Dynamic Persona-Based Calibration (DPBC) step creates the mathematical targets for our Genetic Algorithm. Rather than hardcoding what "good" tone is, it uses a Vector Database to find historically similar emails (K-Nearest Neighbors) and averages their scores. This ensures that the engine evaluates a "Frustrated Client" email differently than a "Friendly Colleague" email.

## I/O Signatures
*   **Input Data:** 
    *   `persona`: `PersonaProfile` (Output from Step 2)
    *   `email`: `HumanEmail` (Output from Step 1)
    *   `vector_db_client`: Connection to local ChromaDB / SQLite-VSS
*   **Output Data:** `DPBCThresholds`

## Core Logic Workflow

### 1. Vectorization Preparation
*   Combine the persona typology and the raw text to create a heavily weighted string:
    `combined_text = "[{persona.typology_classification}] {email.raw_text}"`
*   Pass this string to the embedder (e.g., `sentence-transformers` 384d model).

### 2. K-Nearest Neighbor (KNN) Retrieval
*   Query the Vector DB for `k=5` nearest neighbors using the generated vector.
*   Extract the historical metric scores (`tone_score`, `conciseness_score`, `accuracy_score`) from the metadata of those 5 neighbors.

### 3. Threshold Calculation
*   Average the scores of the 5 neighbors to establish the `DPBCThresholds`.
*   *Math:* `target = sum(scores) / 5`

## Edge Cases & Error Handling
*   **Cold Start (Empty DB):** If the Vector DB has fewer than 5 records (or 0 records), the KNN query will fail or skew. 
    *   **Action:** Catch empty neighbor lists and execute a "Zero-Shot LLM Evaluation". Pass the raw email to the LLM and dynamically ask it to score the Tone, Conciseness, and Accuracy on a 0-10 scale. This returns context-aware fallback thresholds without hardcoding static baselines.
