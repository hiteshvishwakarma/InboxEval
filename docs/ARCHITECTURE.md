# InboxEval Architecture & Vision

## The Core Problem
Evaluating AI-generated emails cannot be done on a universal, static baseline. Human communication is highly subjective and depends entirely on context: role, industry, region, culture, and intent. A perfectly formatted, highly professional email (a "10") is a failure if the user requested a casual message to a close colleague.

To build a world-class, enterprise-grade benchmarking platform, InboxEval must dynamically understand the **Persona** of the user and benchmark against that specific persona's "Human Average."

## The 3-Tier Persona Architecture

To achieve dynamic, persona-driven benchmarking, InboxEval follows a 3-tier architectural roadmap:

### Tier 1: Explicit Onboarding Profiling (Phase 1/MVP)
The system relies on explicit metadata to define the baseline.
- **Mechanism:** Users define their profile (Industry, Role, Tone Preferences, Company Culture) during onboarding.
- **Execution:** The Evaluator Engine (`engine.py`) injects this User Profile directly into the grading prompt, instructing the LLM-as-a-Judge to evaluate the generated email against those specific demographic constraints.
- **Current State:** In our Golden Dataset phase, the *human grader* acts as this tier, manually defining the baseline scores based on the context of each prompt.

### Tier 2: The Persona Classifier (Phase 2)
The system intelligently infers the persona to reduce user friction.
- **Mechanism:** An intermediary, high-speed LLM (e.g., Gemini Flash) acts as a **Context Extractor**.
- **Execution:** Before evaluation, the classifier analyzes the raw user prompt (e.g., "Tell the design team the Figma files are messy") and automatically tags the persona (e.g., `Creative`, `Tech`, `Casual`). These dynamic tags are passed to the Evaluator Engine to adjust the target benchmarks on the fly.

### Tier 3: The "Persona Fingerprint" Vector DB (Phase 3 - Enterprise Gold Standard)
The ultimate, mathematical approach to stylistic RAG (Retrieval-Augmented Generation) evaluation.
- **Mechanism:** The system integrates with the user's actual email history (via Gmail/Outlook APIs).
- **Execution:** 
  1. Historical emails are converted into stylistic embeddings and stored in a Vector DB.
  2. This creates a mathematical **Persona Fingerprint** unique to that specific user.
  3. During evaluation, the system calculates the mathematical distance between the AI-generated email and the user's Fingerprint. 
- **Result:** Instead of relying on LLM-as-a-judge "vibes", the platform provides scientifically backed scores for `Persona Adherence` and `Human Likeness` based on real-world data.
