# The Global AI Email Evaluation Benchmark Framework

> [!IMPORTANT]
> **The Project Manifesto: The Epitome of Innovation**
> This project is not just another weekend experiment. It is designed to be the world-class industry standard for AI email benchmarking. 
> The platform must feature a professional, modern, evidence-based dashboard with standard parameters displayed visually. It must possess full functional controls for interactiveness. It is built to motivate the world and showcase the groundbreaking precision and algorithms that a solo developer, armed with unlimited AI capabilities, can deploy to solve real-world problems. We will never compromise on design, UX, or backend algorithmic precision.

To build a production-grade benchmarking platform that becomes the industry standard, the system should evaluate AI email agents across a standardized suite of tests, generating a "Global Email Score" (similar to a credit score or Lighthouse score for AI emails).

## 1. Core Evaluation Pillars

### A. The Inbound Benchmark (Comprehension & Extraction)
Testing how well an AI understands and processes incoming emails.
*   **Information Extraction (F1 Score):** Ability to pull exact data (Names, Dates, Intents, Budgets) into structured JSON.
*   **Sentiment & Urgency Classification:** Accurately routing "angry" or "urgent" emails.
*   **Thread Context Retention:** Ability to answer questions based on a messy, 15-reply deep email chain.

### B. The Outbound Benchmark (Generation & Personalization)
Testing how well an AI drafts emails (Cold Outreach, Marketing, Support replies).
*   **Grounding/Faithfulness:** Does the email only use facts provided in the prompt (e.g., user's CRM data) without hallucinating features?
*   **Personalization Index:** How well does it incorporate scraped data (e.g., LinkedIn bio) without sounding robotic or creepy?
*   **Tone Adherence:** LLM-as-a-judge scoring on whether the email matches the requested brand voice.
*   **Conciseness Score:** Punishing models that generate overly verbose, "AI-sounding" walls of text.

### C. The Deliverability & Technical Benchmark (Safety & Formatting)
Testing the physical output of the email.
*   **Spam Trigger Detection:** Algorithmic scanning for words/phrases that trigger ESP (Email Service Provider) filters.
*   **Structural Integrity:** Checking for broken Markdown, malformed HTML, or broken URL structures.
*   **Toxicity & PII Leakage:** Guardrail testing to ensure the AI doesn't generate offensive content or leak Personally Identifiable Information.

## 2. Phase 2 Architecture: Closed-Loop Control Systems (Iterative Prompt Refinement)
The initial "Open-Loop" reverse-engineering of human emails into synthetic prompts is prone to information loss. To ensure world-class precision, the system will implement a **Closed-Loop Feedback System** based on Control Theory:
1. **Initial Back-Translation:** The system reads a human email ($E_{human}$) and reverse-engineers a prompt ($P_0$).
2. **Forward Generation:** The system feeds $P_0$ into a model to generate a synthetic email ($E_{synth}$).
3. **Delta Calculation:** The Evaluator Engine grades $E_{synth}$ against $E_{human}$ across all 12 parameters.
4. **Iterative Correction (PID Loop):** If the parameter delta is outside the acceptable tolerance margin ($\pm 0.01$ to $0.05$), the system identifies the missing nuance (e.g., "The tone was too formal, missing the urgency of the original"). It generates an adjusted prompt ($P_1$) and repeats the cycle.
5. **Convergence:** The loop exits only when the prompt mathematically generates an email that mirrors the exact semantic and parametric signature of the original human email.

## 2. Proposed Architecture & Workflow

1.  **The Benchmark Datasets (The "Golden Sets"):** You will need to curate open-source datasets of thousands of scenarios (e.g., "Draft a follow-up to this objection," "Extract the meeting time from this thread").
2.  **The Engine (LLM-as-a-Judge + Deterministic Rules):** 
    *   Use deterministic scripts to test for HTML/Spam/Length.
    *   Use a highly calibrated LLM (like GPT-4o or Claude 3.5 Sonnet) as the "Judge" to score Tone, Faithfulness, and Personalization based on strict grading rubrics.
3.  **The Leaderboard:** A public-facing leaderboard ranking commercial models (GPT-4, Claude, Gemini, Llama) and popular AI Email tools based on their aggregate "Email Eval Score."
4. **The Developer API/SDK:** Allow companies building AI email agents to pipe their outputs through your SDK in their CI/CD pipeline (e.g., `email_eval.test(agent_output, expected_schema)`).

## 3. UI/UX Innovation: The Frontend Architecture
To move beyond naive "1 to 10" grids and establish visual supremacy, the platform implements:
* **The Multi-Select Radar Matrix:** Utilizing `recharts`, users can select multiple LLMs on the leaderboard simultaneously. The system dynamically generates an overlapping Spider Web (Radar Chart) to visually represent the exact error margins and structural deficits (e.g., Tone vs. Factual Accuracy) of multiple models.
* **Shareable Evidence Permalinks:** Evaluation results are saved to a local database and accessible via dynamic Next.js routes (`/eval/[id]`). This allows developers to share cryptographic proof of their model's performance on Twitter or with stakeholders.

## 4. Algorithmic Innovation: Multi-Agent Debate
We abandon the naive single-LLM judge approach. Evaluations are processed via a Multi-Agent Debate algorithm:
1. **Agent 1 (Harsh Critic):** Instantly analyzes the email looking *only* for flaws.
2. **Agent 2 (Constructive Advocate):** Instantly analyzes the email looking *only* for strengths.
3. **The Moderator:** Synthesizes the debate and mathematically issues the final 12-parameter score.
This eliminates confirmation bias and numeric clustering (the tendency for LLMs to safely grade everything an 8/10).

## 5. Go-to-Market Strategy
To become the global standard:
*   **Phase 1:** Launch the "AI Email Leaderboard." Run the top 10 foundational models against your proprietary email dataset and publish the results. This generates massive PR.
*   **Phase 2:** Open-source the base evaluation dataset and metrics library (similar to how DeepEval operates) to gain developer trust.
*   **Phase 2.5 (Evolutionary Prompt Optimization):** Hardcoded absolute scoring (1-10) is fundamentally flawed due to LLM score compression. The Eval Engine uses **Genetic Algorithms with N-way Tournament Selection**. Instead of 1v1, the Refiner generates N mutations simultaneously and the LLM Judge ranks them. 
    * *Genetic Crossover:* If Prompt A wins "Details" but Prompt B wins "Tone", the algorithm extracts the best instructions from both and breeds a "Super Prompt". This guarantees survival-of-the-fittest prompts.
*   **Phase 3 (The Human Arena):** Blind A/B testing playground mimicking LMSYS Chatbot Arena. The UI is strictly 1v1 to prevent human cognitive overload.
    * *KDA-Adjusted Elo (Parameter-Weighted Deltas):* The system doesn't just record a flat Win/Loss. The backend calculates parameter-wise victory margins (e.g., Model A won overall, but Model B won on Formatting). Similar to CS2/Valorant hidden MMR, Model B loses significantly less Elo because of its high performance on specific parameters.
    * *The Telemetry Engine:* Implement Anti-Spam filters (Read-Velocity tracking) and Honeypot Calibrations to ensure annotators are grading authentically. Assign an "Annotator Elo" to penalize noisy voters.
    * *Constitutional AI Simulator:* Utilize `arena_bot.py` to bypass the human bottleneck. The bot implements Anthropic's true 2-step Constitutional AI pipeline: it adopts a persona from a dynamic "Emotional State Matrix" (e.g., Empathetic HR, Anxious Lawyer), critiques the output against a specific constitutional principle, and then votes. This perfectly simulates the emotional variance of crowdsourcing.
    * *Data Collection:* Log all raw interactions into `arena_training_dataset.jsonl` for future RLHF model training.
*   **Phase 4 (RLHF & DPO Preference Data Collection):** The raw pairwise preference labels generated by humans (and the simulator) in the Arena are captured and logged (e.g., `[Prompt, Model_A, Model_B, Winner]`). This is the industry standard for Reinforcement Learning from Human Feedback (RLHF). This invaluable preference dataset is NOT used for the factual Golden Dataset, but rather published for researchers to fine-tune open-source models to perfectly align with human writing preferences.

## 6. The DPBC Vector Architecture (Dynamic Persona-Based Calibration)
A fatal flaw in naive evaluation systems is hardcoding static thresholds (e.g., demanding a `9/10` across all emails). A 5-word angry refund demand has radically different standards for "Professionalism" than a 500-word Fortune 500 M&A proposal. 
To achieve world-class precision, InboxEval abandons static tags and utilizes **Latent Space Vector Mathematics**:
1. **Molecular Vector Embeddings:** When a raw email is ingested, it is passed through a lightweight embedding model (e.g., `all-MiniLM-L6-v2`). This instantly converts the email's semantic "vibe" (Tone, Intent, Domain, Formality) into a 384-dimensional vector, breaking the persona down to a molecular level without relying on brittle text tags.
2. **K-Nearest Neighbors (KNN) Semantic Fallback:** When evaluating a new email, the system queries a high-speed Vector DB (like ChromaDB or SQLite-VSS) for its 5 closest semantic neighbors in the historical dataset. 
3. **Dynamic Threshold Blending:** The engine calculates the average acceptable Elo/Score of those 5 specific neighbors. If an email is highly unique, it mathematically borrows baseline expectations from its closest semantic relatives, natively solving the "Cold Start / Data Sparsity" problem.
4. **The Global Fallback:** If the Vector DB is completely empty (Day 1), the system does NOT default to a hardcoded `8.0`. It falls back to the rolling average of the entire current Golden Dataset, ensuring the baseline always scales with reality.

## 7. Step-by-Step Pipeline (From 0 to 1)

### Pipeline A: Golden Dataset Generation (Backend Prep)

**Executive Summary:**
Pipeline A is the internal, closed-loop engine responsible for generating the world-class `golden_dataset.jsonl`. It ingests historical human emails, extracts their persona via Vector Embeddings, and uses Evolutionary Prompt Optimization to reverse-engineer flawless synthetic prompts. The system mathematically prevents generational degradation via Elitism and optimizes for Delta Minimization against Dynamic Persona-Based Calibration (DPBC) thresholds. Crucially, the engine employs a Dual-Scoring Judge utilizing Persona-Dynamic Constraints. This prevents the AI from defaulting to robotic structures, forcing the Genetic Algorithm to evolve optimal prompts that strictly adhere to the diverse behavioral constraints of their assigned human demographic. These demographics are not statically hardcoded; the system dynamically synthesizes 5 unique, context-aware human personas on the fly for every single email to ensure infinite variability.

**Architecture Blueprint:**
* **Phase 1 (Preparation):** Raw Ingestion -> Persona Extraction -> DPBC Vectorization
* **Phase 2 (Genesis):** Lazy Base Prompt Generation -> Dynamic Context-Aware Persona Synthesis -> 5-Way Mutation
* **Phase 3 (Evaluation):** Forward Generation -> Isolated Parameter Judging -> KDA Matrix & Delta Ranking
* **Phase 4 (Evolution):** Closed Feedback Loop -> Polygenic Crossover (Super Prompt) -> Elitism / Early Stopping -> Dataset Commit

**In-Depth Execution Steps:**
This is the step-by-step internal process InboxEval uses to build the flawless dataset.
1. **Raw Ingestion (`mass_ingestion.py`):** Harvests a real, historical human email ($E_{human}$).
2. **Reverse Engineering & Persona Extraction:** Before any prompts are written, an Evidence-Based Classifier LLM analyzes $E_{human}$. It extracts the exact intent, context, and a molecular Persona Profile (Domain, Category, Sentiment). 
3. **Vectorization:** The extracted Persona Profile and the $E_{human}$ text are embedded into a semantic vector and stored. This allows the system to query the Vector DB (via KNN) to find the exact historical DPBC thresholds (e.g., Tone: 6.5, Conciseness: 4.2) expected for this specific persona. We do not demand a "perfect 10"; we demand adherence to the persona's historical threshold.
4. **Base Prompt Generation (Persona-Augmented Benchmarking):** The system generates a base prompt ($P_0$) to recreate $E_{human}$. *CRITICAL RESEARCH CONSTRAINT:* We do NOT hardcode a single prompting style, nor do we use a static list of personas. Industry research proves models suffer from "Prompt Jitter." Therefore, we utilize a **Dynamic Prompt Typology Matrix**. The system passes the context of the ingested email to an LLM, which dynamically synthesizes 5 diverse, contextually relevant "Prompt Writer Personas" on the fly (e.g., generating "The Furious CEO" and "The Stressed IT Manager" specifically for a B2B Server Rack email).
5. **Genesis Mutation (Prompt Diversity):** From $P_0$, the system generates 5 vastly different prompt mutations, each adopting one of the newly synthesized dynamic personas. This guarantees the Golden Dataset tests models against real-world human linguistic variability across an infinite, non-static spectrum of demographics.
6. **Forward Generation & Isolated Evaluation:** All 5 prompts are fed to an LLM to generate 5 synthetic emails ($E_{synth}$). *CRITICAL CONSTRAINT (Dual-Scoring & Persona Deviation):* The LLM Judge executes a dual-evaluation in complete isolation. 
   - **Score A (Output):** It measures the Delta Minimization of the generated email against the human original. 
   - **Score B (The Prompt Itself):** It calculates a **Persona Deviation Penalty**. The Judge cross-references the prompt's syntax against its assigned Typology Matrix Persona. If a "Lazy Minimalist" prompt utilizes rigid JSON, or a "Tech Power User" prompt uses messy slang, the prompt receives a massive mathematical penalty. This forces the Genetic Algorithm to evolve optimal prompts that strictly adhere to the psychological and structural reality of diverse human demographics.
7. **The KDA Matrix & N-Way Tournament Selection (Delta Minimization):** The system compiles the isolated evaluations. *CRITICAL MATHEMATICAL CORRECTION:* The Judge does NOT rank the prompts based on the highest absolute score (e.g., an 8.0 is not necessarily better than a 7.0). It ranks them 1st through 5th based on **Delta Minimization** (minimizing the absolute error between the generated score and the specific historical DPBC target). The prompt whose $E_{synth}$ has the smallest delta to the human baseline wins. Instead of discarding the bottom 3 outright, the system generates a KDA Matrix identifying if any lower-ranked prompt won a specific parameter by having the smallest delta (e.g., Prompt 5 lost overall, but had the closest "Tone").
8. **The Closed Feedback Loop:** The Judge provides explicit, written feedback on *why* the generated emails failed to perfectly mirror the human email.
9. **Polygenic Crossover (Multi-Parent Breeding):** The Genetic Algorithm ingests the feedback loop and the KDA Matrix. It takes the overall winner (Rank 1) as the base, but executes a **Multi-Parent (Polygenic) Crossover**. It mathematically extracts the absolute best traits from *any* of the 5 prompts (e.g., borrowing the tone instructions from Prompt 5) to synthesize the ultimate "Super Prompt" (Generation 1).
10. **DPBC Loop & Elitism (Preventing Degradation):** To prevent generational degradation (where Gen 2 is worse than Gen 1), the engine uses **Elitism**: The all-time best prompt (the one with the lowest overall Delta) is always carried over untouched into the next generation's tournament. The Super Prompt generates 4 new mutations to battle the reigning Champion. 
11. **Early Stopping (Plateau Detection):** The loop repeats until an $E_{synth}$ mathematically crosses the DPBC thresholds (Delta hits near 0). However, if the Delta fails to shrink for 2 consecutive generations (a flat, linear graph indicating wasted resources), the system triggers an **Early Stop**, taking the reigning Champion to prevent resource drain.
12. **Commit:** The winning lazy human prompt and the target $E_{human}$ are saved as a perfect pair to the Golden Dataset.

### 8. Codebase Architecture & Data Infrastructure

To ensure enterprise-grade maintainability, Pipeline A strictly enforces an **AI-First Modular Architecture** and a **Dual-Database Infrastructure**.

**The Dual-Database Infrastructure:**
*   **Database A: The Vector DB (Semantic Engine):** Utilizes ChromaDB or SQLite-VSS (local). Used exclusively in Step 3 to store the semantic embeddings of human emails. This enables the calculation of DPBC thresholds via K-Nearest Neighbors (KNN).
*   **Database B: The Relational DB (Telemetry & RLHF):** Utilizes PostgreSQL or a robust SQLite file. Used by the Orchestrator to log every single input, output, mutation, KDA Matrix, and feedback loop across all 12 steps. This creates a massive RLHF (Reinforcement Learning from Human Feedback) dataset for future open-source model training.

**The Modular Folder Structure:**
Instead of monolithic scripts, the engine operates as a decoupled Orchestrator managing 12 atomic node files:
```text
src/engine/
└── golden_dataset_generator/
    ├── orchestrator.py                 <-- Master logic loop
    ├── schemas.py                      <-- Strict Pydantic Data Models
    └── engine_steps/
        ├── step_01_ingest.py           <-- Fetches the raw human email
        ├── step_02_persona_extract.py  <-- Extracts Domain/Category/Intent
        ├── step_03_vectorization.py    <-- Queries Vector DB for DPBC Thresholds
        ├── step_04_persona_synthesis.py<-- Dynamically generates 5 Prompt Personas
        ├── step_05_genesis_mutation.py <-- Spawns the 5 diverse prompts
        ├── step_06_evaluator.py        <-- Forward generation & dual-scoring LLM judge
        ├── step_07_kda_ranking.py      <-- Calculates Delta Minimization & ranks 1-5
        ├── step_08_feedback_loop.py    <-- Generates explicit written feedback
        ├── step_09_crossover.py        <-- Polygenic Breeding (Genetic Algorithm)
        ├── step_10_elitism.py          <-- Crowns the Reigning Champion
        ├── step_11_early_stop.py       <-- Detects mathematical plateaus
        └── step_12_commit.py           <-- Saves to golden_dataset.jsonl
```

### Pipeline B: The Eval Engine (User/Client Facing)
This is how a corporate client uses InboxEval to grade their brand-new, unknown AI model.
1. **Input Submission:** The client inputs their AI model API key into the InboxEval Engine.
2. **Batch Generation:** The Engine feeds the client's model 100 perfect prompts from the Golden Dataset.
3. **The Anchor Baseline:** Simultaneously, the Engine feeds the same 100 prompts to a locked Anchor Model (e.g., GPT-4o pinned at exactly `1500 Elo`).
4. **Pairwise Evaluation:** The Engine's LLM Judge blindly compares the Client Model's output against the Anchor Model's output in a 1v1 battle for all 100 emails.
5. **Elo Calibration:** Based on win/loss margins, the Client Model's Elo rating shifts. 
6. **Final Report:** The client receives a mathematically rigorous report: *"Your model achieved a global Elo of 1420. It is 5% worse than GPT-4o overall, but 12% better at B2B Sales Intent based on semantic vector clustering."*
# The Elite Corporate & Historical Golden Dataset Taxonomy

To build a world-class LLM evaluation benchmark for email generation, our Golden Dataset will pull from the following vast, elite categories. The dataset will be populated using real historical text combined with high-end synthetic "reverse-engineered" prompts via Groq's APIs.

## 1. The "Famous Leaks" Category (Historical Human Baselines)
These are verified, real-world emails from high-stakes situations. We use the raw text of these emails and reverse-engineer the prompt that generated them.

*   **The Enron Email Dataset (2001)**: The gold standard for corporate linguistics. Over 500,000 real emails spanning deep energy sector jargon, internal corporate politics, legal panic, and compliance reporting.
*   **The Sony Pictures Hack (2014)**: High-stakes Hollywood negotiations, PR crises, talent management disputes, and frank (often brutal) executive candor between producers and studio heads.
*   **Tech Titan Leaks**: 
    *   **Elon Musk (Tesla/X/SpaceX)**: Famous "Return to Office" mandates, aggressive supply chain sabotage warnings, and mass layoff communications.
    *   **Mark Zuckerberg (Facebook/Meta)**: Strategic pivot memos, internal security warnings, and aggressive resignation demands to leakers.
    *   **Steve Jobs (Apple)**: The "Top 100" retreat memos, aggressive talent poaching disputes with Google/Adobe, and visionary product roadmaps.
    *   **Bill Gates (Microsoft)**: The legendary "Internet Tidal Wave" memo outlining massive shifts in tech strategy.
    *   **Sam Altman (OpenAI)**: Internal communications regarding board disputes and rapid scaling challenges.

## 2. The Fortune 500 Corporate Matrix
Highly realistic, domain-specific emails covering the nuanced communication styles of various elite industries, companies, and scenarios.

*   **Big Tech (FAANG)**
    *   *Companies*: Google, Amazon, Apple, Netflix, Meta, Microsoft.
    *   *Scenarios*: Cloud architecture migration proposals (AWS/GCP), post-mortem incident reports (SEV-1 outages), cross-functional product alignment, equity compensation explanations.
*   **High Finance & Wall Street (Investment Banking/Hedge Funds)**
    *   *Companies*: Goldman Sachs, JPMorgan Chase, Morgan Stanley, Citadel, Bridgewater.
    *   *Scenarios*: High-stakes M&A deal updates, SEC compliance audits, earnings call preparation memos, venture capital term sheet negotiations, margin call alerts.
*   **Big 4 Consulting & Accounting**
    *   *Companies*: Deloitte, PwC, EY, KPMG, McKinsey, BCG.
    *   *Scenarios*: Synergistic project proposals, risk mitigation strategy decks, partner-level client relationship management, massive corporate restructuring announcements.
*   **Healthcare & Biotech**
    *   *Companies*: Pfizer, Johnson & Johnson, UnitedHealth.
    *   *Scenarios*: HIPAA-compliant patient communication, FDA regulatory submissions, clinical trial phase updates, supply chain refrigeration logistics.
*   **Logistics, Automotive & Manufacturing**
    *   *Companies*: Ford, Boeing, FedEx, Maersk.
    *   *Scenarios*: Supply chain disruption alerts, vendor pricing disputes, shipping freight manifest negotiations, union negotiation updates, factory floor safety recalls.
*   **Entertainment, Media, & Sports**
    *   *Companies*: Disney, Warner Bros, NFL, FIFA, Universal Music Group.
    *   *Scenarios*: Hollywood casting agency negotiations, professional athlete PR crisis management, sponsorship contract disputes, tour cancellation notices.
*   **Agriculture & Energy**
    *   *Companies*: ExxonMobil, Chevron, John Deere, Monsanto.
    *   *Scenarios*: Oil spill environmental impact reporting, commodities trading disputes, farming equipment supply chain delays.

## 3. The Everyday Human Experience
The standard consumer-level emails that form the backbone of internet communication, capturing a vast spectrum of emotion and intent.

*   **Administrative & HR**: PTO requests, salary negotiations, resignation letters, harassment complaints, maternity leave planning.
*   **Customer & Vendor Relations**: Angry restaurant reviews, refund demands, apologizing for a delayed shipment, B2B SaaS onboarding.
*   **Academic & Personal**: Emailing a professor for an extension, drafting a roommate agreement, apologizing to a friend for missing a wedding.
*   **Cold Outreach & Networking**: B2B SaaS sales pitches, networking requests to alumni, recruiter intro emails, seeking venture capital funding.

---
*Note: This taxonomy is actively used by the ingestion pipeline to ensure the InboxEval Golden Dataset remains the most diverse and rigorous email benchmark in the AI industry.*

## 6. Frontend Architecture: The 3D Spatial UI & WebGL Optimization

To elevate the UX beyond standard dashboards, InboxEval employs a First-Person Spatial UI (a 3D "Server Room" lobby) built with React Three Fiber (R3F) and Three.js. This serves as an interactive hub for accessing the evaluation arenas and easter eggs.

### Optimization & Performance Strategy (WebGL/WebGPU)
To ensure accessibility across all hardware (from lightweight i3 laptops to high-end Apple Silicon), the 3D architecture strictly adheres to dynamic rendering pipelines:
1.  **Mathematical Primitives vs. Meshes:** The v1 prototype uses pure mathematical primitives (`boxGeometry`, `planeGeometry`) rather than heavy `.glb` files. This eliminates network payload and ensures near-instant initialization.
2.  **Dynamic Device Pixel Ratio (DPR) Scaling:** The engine employs `@react-three/drei`'s `<PerformanceMonitor>`. It tracks frame rendering times dynamically. If the client GPU struggles to maintain 60 FPS, the engine autonomously degrades the resolution (DPR drops to 0.5x). Conversely, powerful GPUs scale up to 1.5x Retina resolution.
3.  **Client-Side Hydration & Event Management:** 
    *   Next.js SSR boundaries are strictly maintained (`isClient` toggles) to prevent server hydration mismatches with WebGL contexts.
    *   PointerLock API security constraints are managed by stopping click event propagation (`e.stopPropagation()`) on floating HTML elements to prevent erroneous browser security exceptions.
4.  **Math-Based Collision Detection:** To avoid the overhead of heavy physics engines (like Cannon.js or Rapier), the first-person controller implements strict Axis-Aligned Bounding Box (AABB) collision checks, calculating positional arrays directly in the `useFrame` render loop.

### Phase 2: Spatial UI Expansion (The Server Room Ecosystem)
To fully immerse the user in the "Hacker Art" aesthetic, the 3D lobby will be expanded beyond the basic desk and server rack. Each element represents a functional core of the InboxEval backend:
*   **The Core Database (Visualized):** A glowing cylindrical structure representing the `golden_dataset.json`. It grounds the room and serves as a visual anchor for data exports.
*   **Data Conduits & Cables:** Geometric lines spanning the ceiling and floor, physically connecting the Core Database, the Desk, and the Server Rack, reinforcing the puzzle mechanics (e.g., using Pliers to splice connections).
*   **The Live Leaderboard Wall:** A massive floating HTML monitor within the 3D space that streams live ELO data from the backend, providing passive evaluation data before the user even enters the Arena.
