---
name: inboxeval_manager
description: Activate this skill automatically during any workflow within the InboxEval project to enforce project-specific standards, atomic Git commits, and code quality.
---

# InboxEval Project Manager

This skill contains the master instructions, context, and guardrails for the **InboxEval** project. You MUST follow these instructions strictly whenever working inside the `/Users/hiteshvishwakarma/development/InboxEval` workspace to prevent hallucinations and ensure production-grade quality.

## 1. Project Context & Vision
- **Name**: InboxEval
- **Goal**: Build the global standard benchmark for AI-generated emails. It scores emails based on Tone, Spam/Deliverability, and Hallucination.
- **Phases**: 
  1. Python Engine & Golden Dataset (Current)
  2. Open Source Leaderboard
  3. SaaS Dashboard (Next.js/Vite)
- **Constraint**: Do not add unnecessary bloat or complex features that do not directly serve the immediate phase. Keep the README crisp and short.

## 2. Git & Version Control Mandates (Atomic Commits)
To prevent complications and allow for easy cherry-picking, you MUST commit every single molecular change.
- **Rule**: Never batch unrelated changes into a single commit. 
- **Rule**: After every logical step (e.g., creating a file, updating a function, adding a test), immediately run `git add` and `git commit`.
- **Rule**: Use descriptive, standard commit messages (e.g., `feat: added evaluate_tone function`, `fix: corrected regex in spam checker`).
- **Rule**: Push changes to the remote repository frequently.

## 3. Best Practices & Code Quality
- Write clean, modular, and production-grade Python code.
- Always include type hints and basic docstrings for major functions.
- If an LLM is asked to generate code, ensure the logic directly aligns with the InboxEval goals. If you detect a hallucination (e.g., proposing an irrelevant feature), self-correct immediately based on this skill's context.

## 4. Continuous Documentation (The Internal Playbook)
- **Rule**: You MUST automatically document all new architectural decisions, evaluation logic, and testing strategies into the internal artifact (`solo_developer_roadmap.md`) without waiting for the user to instruct you to do so. Git commits track the code, but the artifact must track the *reasoning and architecture*.
