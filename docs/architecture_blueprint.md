# InboxEval Golden Dataset Evolutionary Engine
## Executive Summary
This project is an advanced, multi-agent AI pipeline designed to generate an adversarial, high-quality "Golden Dataset" for finetuning language models. It leverages an evolutionary algorithm to pit LLMs against each other in a zero-sum game, mutating human emails into highly targeted, persona-driven synthetic data.

---

## 1. Architecture Blueprint
The system follows a strict, 13-Step Finite State Machine (FSM) pipeline that continuously loops until convergence thresholds are met.

1. **Step 00 (Ingestion/Cleaning):** Download raw Enron corpus, filter out noise, and store in local SQLite.
2. **Step 01 (Backtranslation):** Extract underlying prompts and context from raw human emails.
3. **Step 02 (Vectorization & Storage):** Create local embeddings of the raw email via `sentence-transformers` into ChromaDB.
4. **Step 03 (Persona Extraction):** Deduce the original author's persona structure (formality, domain, traits).
5. **Step 04 (Threshold Generation - DPBC):** Calculate Dynamic Persona Boundary Constraints based on KNN proximity.
6. **Step 05 (Persona Synthesis):** Generate adversarial synthetic personas to test the model's boundaries.
7. **Step 06 (Genesis Mutation):** Mutate the raw email into synthetic emails adopting the new personas.
8. **Step 07 (Evaluator / Reward Hack Check):** Score the synthetic emails against DPBC thresholds (Tone, Conciseness, Accuracy).
9. **Step 08 (KDA Ranking):** Calculate the Knowledge Distillation Adversarial Matrix to rank mutations.
10. **Step 09 (Feedback Loop):** A hyper-critical Judge model evaluates failures and outputs Markdown critique.
11. **Step 10 (Crossover):** Merge the best strategies from winning mutations into a Super Prompt.
12. **Step 11 (Elitism):** Generate new Challenger Prompts based on the Super Prompt.
13. **Step 12 (Convergence & Golden Export):** Check against threshold limits. If passed, export to Golden Dataset SQLite.

---

## 2. Dynamic Persona Boundary Constraints (DPBC)
To prevent the LLMs from "reward hacking" (e.g., maximizing politeness by sacrificing the original meaning), DPBC calculates a bounding box around the original email's vector. Synthetic mutations must score highly while remaining within the strict semantic boundary of the DPBC.

## 3. Knowledge Distillation Adversarial (KDA) Matrix
A zero-sum matrix scoring system where multiple mutated prompts compete. The KDA Matrix determines the absolute winner across three sub-metrics (Tone, Conciseness, Accuracy), forcing the crossover step to only inherit traits from empirical winners.

---

## 4. The 2D Proactive Round-Robin Rotator
To handle thousands of complex Pydantic JSON evaluations, the engine uses a highly specialized `DynamicGroqRotator`.

### Routing Matrix (Empirical 3/3 Baseline)
The engine analyzes the exact Pydantic schema requested and routes it to the specific models mathematically proven to support that level of cognitive load:
- **Step 01 (Native JSON):** Rotates equally across all 7 capable models.
- **Steps 02, 08, 09 (Medium Constraints):** Rotates across `llama-3.1-8b-instant` and `llama-3.3-70b-versatile`.
- **Steps 04, 10 (List Extraction):** Rotates across `llama-3.1`, `llama-3.3`, `gpt-oss-120b`, `gpt-oss-20b`, and `qwen3.6-27b`.
- **Steps 05 & 06 (Extreme Complexity):** Hard-locked to `llama-3.3-70b-versatile` to prevent context collapse and 400 Bad Request errors.

### Rotational Load Balancing
- Advances both the **API Key** and the **Model** simultaneously on a master incrementing counter.
- Prevents "burst-to-death" by splitting traffic across 14 API keys evenly (yielding ~420 RPM and ~420k TPM capacity out of the box).
- Employs a non-skipping, `N*2` attempt loop. A 429 Rate Limit naturally resolves by advancing the key, and a 400 Hallucination error naturally resolves by advancing the model. Ultimate failures throw `CRITICAL_LLM_FAILURE` to be natively logged in the SQLite tracker.

---

## 5. Engine v3: T-Shaped Decoupled Architecture
To solve the "Meta-Leak" context window corruption and maximize GPU throughput, Engine v3 implements a fully decoupled T-Shaped pipeline:

1. **Horizontal Ingestion (Phase 1):** 
   - Responsible strictly for semantic extraction and baseline calculation.
   - Operates independently on raw emails to generate the `11-Axis Persona` (vLLM API) and the `DPBC Thresholds` (Local CPU Embedding Math) simultaneously.
   - Pushes pre-calculated, pristine JSON constraints into the SQLite database.

2. **Vertical Evolution (Engine v3):** 
   - Stripped of all ingestion and extraction overhead. 
   - Dedicated entirely to the Genetic Algorithm FSM (Mutations, Evolutions, Judgements, Crossovers).
   - Starts directly at **Step 05 (Persona Synthesis)** by ingesting the pre-calculated DPBC and Persona JSON targets from the database, eliminating context pollution.

### The DiversitySampler Feedback Loop
Engine v3 achieves **Zero-Overhead Stratified Diversity Sampling** using a specialized Database Feedback Loop:
- Bypasses static `ORDER BY RANDOM()` queues.
- Dynamically queries the `golden_dataset` table to analyze current distribution skews (e.g., MICRO vs LONG emails).
- Quantitatively targets and fetches raw emails from Phase 1 that belong to the most mathematically underrepresented category, balancing the dataset at the DB level with < 5ms latency.

---

## 6. Engine v4: Production GCP Scaling (Current)
To solve the `SQLITE_BUSY` deadlocks and strict API rate limits observed in v3 when scaling to 60-concurrent GCP workers, Engine v4 introduces:

1. **The Concurrency Model:** Scales to 60-concurrent FSMs using `asyncio.Semaphore`, decoupling the Orchestrator from the DB completely.
2. **The Database Optimization:** Defeats DB write locks by using `PRAGMA journal_mode=WAL;` and enforcing a single batched `.commit()` for every 100 rows, rather than inline worker commits.
3. **The LLM Resilience Loop:** Wraps all four LLM generation boundaries in `Tenacity` retry blocks with `reraise=True` to gracefully handle Pydantic `ValidationErrors` and intercept JSON hallucinations without crashing the FSM.
4. **Static-First Cache Design:** Prompts are mathematically structured to strip dynamic variables from the System Prompt into the User Prompt, guaranteeing 100% vLLM Prefix Cache hits (0ms prefill latency).
