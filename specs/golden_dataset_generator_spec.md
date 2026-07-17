# Technical Specification: Golden Dataset Generator (Engine)

## System Overview
This engine is a highly modular, 12-step evolutionary genetic algorithm. It takes a raw human email and mathematically reverse-engineers the optimal LLM prompt required to generate it. 
**Objective:** Delta Minimization (Absolute Error) against Dynamic Persona-Based Calibration (DPBC) thresholds.

## Core Directives (AI-First Architecture)
*   **Semantic Naming:** All files and variables must reflect their exact domain purpose. (No `pipeline_a`).
*   **Extreme Modularity:** One node = One file. No monolithic functions.
*   **Schema Strictness:** Pydantic models define all inputs and outputs.
*   **Deterministic Orchestration:** `orchestrator.py` handles loop logic; `engine_steps/` handles execution.

---

## Technical Step Mapping

### PHASE 1: PREPARATION

#### Step 1: Raw Ingestion
*   **File:** `engine_steps/step_01_ingest.py`
*   **Input:** `raw_text` (str), `metadata` (Dict)
*   **Logic:** Wraps the text in the `HumanEmail` schema and assigns a UUID.
*   **Output:** `HumanEmail`

#### Step 2: Persona Extraction
*   **File:** `engine_steps/step_02_persona_extract.py`
*   **Input:** `HumanEmail`, `llm_client`
*   **Logic:** Uses structured output (Instructor/Pydantic) to force the LLM to extract Intent, Domain, Sentiment, and a Typology Tag.
*   **Output:** `PersonaProfile`

#### Step 3: Vectorization & DPBC Thresholds
*   **File:** `engine_steps/step_03_vectorization.py`
*   **Input:** `PersonaProfile`, `HumanEmail`, `vector_db_client`
*   **Logic:** Embeds `[Typology] Text` into 384d vector. Queries local ChromaDB for 5 K-Nearest Neighbors. Averages historical scores.
*   **Fallback:** If DB is empty, return global baseline (`Tone: 7.0`, `Conciseness: 5.0`, `Accuracy: 8.0`).
*   **Output:** `DPBCThresholds`

---

### PHASE 2: GENESIS

#### Step 4: Dynamic Persona Synthesis
*   **File:** `engine_steps/step_04_persona_synthesis.py`
*   **Input:** `HumanEmail`, `PersonaProfile`, `llm_client`
*   **Logic:** Prompts LLM to analyze the email context and generate 5 highly diverse, contextual 'Prompt Writer Personas'. 
*   **Output:** `List[str]` (Array of 5 personas)

#### Step 5: Genesis Mutation
*   **File:** `engine_steps/step_05_genesis_mutation.py`
*   **Input:** `HumanEmail`, `PersonaProfile`, `List[str]` (personas), `llm_client`
*   **Logic:** Iterates over the 5 personas. Prompts LLM to write a base prompt *strictly constrained* by the assigned persona's behavioral style.
*   **Output:** `List[PromptMutation]` (Array of 5 prompts, `generation_num=0`)

---

### PHASE 3: EVALUATION

#### Step 6: Forward Generation & Dual-Scoring
*   **File:** `engine_steps/step_06_evaluator.py`
*   **Input:** `List[PromptMutation]`, `HumanEmail`, `DPBCThresholds`, `llm_client`
*   **Logic:** 
    1. Feeds each mutation to LLM to generate `synthetic_text`.
    2. Uses LLM-as-a-Judge to score absolute Tone, Conciseness, Accuracy.
    3. Calculates Deltas: `abs(target - score)`.
    4. **Dual-Scoring:** Checks if the prompt text violated its Typology Persona (e.g., minimalist using JSON). Applies `persona_deviation_penalty`.
    5. Calculates `overall_delta` (sum of deltas + penalty).
*   **Output:** `List[EvaluatedEmail]`

#### Step 7: KDA Matrix & Ranking
*   **File:** `engine_steps/step_07_kda_ranking.py`
*   **Input:** `List[EvaluatedEmail]`, `generation_num`
*   **Logic:** Finds the mutation with the lowest `overall_delta` (The Winner). Finds individual winners for lowest Tone, Conciseness, and Accuracy deltas.
*   **Output:** `KDAMatrix`

---

### PHASE 4: EVOLUTION

#### Step 8: Closed Feedback Loop
*   **File:** `engine_steps/step_08_feedback_loop.py`
*   **Input:** `KDAMatrix`, `HumanEmail`, `DPBCThresholds`, `llm_client`
*   **Logic:** Prompts LLM to write explicit, analytical feedback on *why* the generated emails failed to perfectly hit the DPBC Deltas.
*   **Output:** `JudgeFeedback`

#### Step 9: Polygenic Crossover
*   **File:** `engine_steps/step_09_crossover.py`
*   **Input:** `KDAMatrix`, `JudgeFeedback`, `llm_client`
*   **Logic:** Uses the Overall Winner as a base. Injects winning traits from the individual parameter winners (e.g., Tone from Prompt B, Accuracy from Prompt C).
*   **Output:** `SuperPrompt`

#### Step 10: Elitism Loop
*   **File:** `engine_steps/step_10_elitism.py`
*   **Input:** `SuperPrompt`, `next_gen_num`, `llm_client`
*   **Logic:** Takes the reigning Champion SuperPrompt. Carries it over untouched. Generates 4 new mutations attacking its weaknesses based on the feedback loop.
*   **Output:** `List[PromptMutation]` (Size: 5. 1 Champion + 4 Challengers).

#### Step 11: Early Stopping (Plateau Detection)
*   **File:** Handled natively in `orchestrator.py` via `_check_convergence()`
*   **Input:** `KDAMatrix`, `GenerationState`
*   **Logic:** If `overall_delta` hits acceptable margin (~0.05), or if the `overall_delta` fails to improve for 2 consecutive generations, trigger early stop.
*   **Output:** `bool` (Converged state)

---

### PHASE 5: SERIALIZATION / EXPORT

#### Step 12: Golden Record Export
*   **File:** `engine_steps/step_12_golden_record_export.py`
*   **Input:** `SuperPrompt`, `HumanEmail`
*   **Logic:** Pairs the winning prompt with the target email. Appends as a perfect tuple to `data/golden_dataset.jsonl`.
*   **Output:** `None` (Disk Write)
