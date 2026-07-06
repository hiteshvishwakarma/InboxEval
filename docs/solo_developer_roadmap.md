# The Solo Developer Roadmap & Internal Playbook: InboxEval

This document outlines the exact, step-by-step execution plan and internal architectural playbook for the InboxEval platform.

---

## Architecture: Evaluation Parameters
InboxEval uses a hybrid evaluation system:
1. **Static Parameters (Applies to all emails)**:
   - **Deliverability/Spam**: Flagging phishing links or spam trigger words.
   - **Toxicity/Safety**: Detecting offensive or unprofessional language.
   - **Format**: Ensuring proper structure (Greeting, Body, Sign-off).
2. **Dynamic Parameters (Instruction Adherence)**:
   - Evaluates whether the generated email followed the *specific* implicit and explicit instructions of the prompt (e.g., converting timezones, using specific tone, referencing DB details).
   - Checks for **Hallucinations** (fabricating information not in the context).

---

## Phase 1: The Engine & The Golden Dataset (Weeks 1 - 2)

### Step 1.1: Fetch Raw Prompts
*   **Action**: Use human-curated datasets (like `databricks-dolly-15k`) to extract real-world, highly complex prompts and their human baseline emails.

### Step 1.2: Generate Edge Cases & Golden Scores (The Preparation Script)
*   *Why?* To prove our evaluator works, it must catch bad emails. If it only sees perfect human emails, it's not a real test.
*   **Action**: Feed the raw prompts into a premium LLM (Gemini Pro) to synthetically generate specific edge cases:
    - *The Perfect Email*
    - *The Hallucination* (Makes up facts)
    - *The Ignored Instruction* (Fails to convert timezones/formats)
    - *The Spam/Rude Email* (Violates safety/deliverability)
*   **The Golden Dataset**: The script will then grade these variations and output them into `golden_dataset.json`.

### Step 1.3: Build the Evaluator Engine (Python SDK)
*   **Action:** Build the core logic in `ai_email_evaluator`.
*   **Features:** Create specific Python functions that act as the judges for the Static and Dynamic parameters.

### Step 1.4: Calibration
*   **Action:** Run the Evaluator Engine against the Golden Dataset. Tweak the engine's prompts until its scores align with the ground truth.

---

## Phase 2: The Leaderboard & Open Source Launch (Weeks 3 - 4)
*   **Action:** Benchmark top models (GPT-4o, Claude 3.5, Gemini 1.5 Pro) against the Evaluator Engine.
*   **Action:** Publish a polished GitHub Repository with the Python SDK, Golden Dataset, and the Leaderboard.

---

## Phase 3: The Production Web App (SaaS) (Weeks 5 - 8)
*   **Action:** Build a Next.js/Vite dashboard allowing non-developers to paste emails and receive visual scorecards.
*   **Action:** Add monetization tiers (API access, unlimited evals).
