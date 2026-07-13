# InboxEval: The AI Email Benchmark & Control System

InboxEval is not just another weekend script. It is an enterprise-grade evaluation platform and closed-loop control system designed to become the global standard for grading AI-generated emails.

## 🎯 The Goal & Approach
To move beyond naive "1 to 10" scoring grids, InboxEval implements a multi-tiered architecture that rivals enterprise AI labs (like OpenAI and Anthropic):

1. **The 12-Parameter Sandbox:** An automated pipeline that grades models on precise metrics like Factual Accuracy, Toxicity, and Tone Adherence using a Multi-Agent Debate algorithm (a Harsh Critic vs. a Constructive Advocate).
2. **The Pairwise Elo Arena:** A blind A/B testing dashboard where models fight head-to-head.
3. **The Telemetry Engine:** An anti-spam filter that tracks Human "Time-to-Vote" (Read Velocity) and Honeypot calibrations to shadow-ban noisy human annotators.
4. **Constitutional AI Simulator (`arena_bot.py`):** To bypass the "Solo Dev Hurdle" of not having thousands of humans, we built a bot that uses an "Emotional State Matrix" (e.g., Anxious Lawyer, Empathetic HR) to critique and vote on emails exactly like Anthropic trains Claude.

## 📚 Official Documentation Navigation
All architectural decisions, roadmaps, and calibration guides are heavily documented and interlinked in the `docs/` directory. If you want to understand the exact mechanics of how this system works, read these in order:

1. [**AI Email Eval Framework (The Manifesto)**](docs/ai_email_eval_framework.md): Start here. Contains the complete Go-to-Market strategy, the core 12-parameter evaluation pillars, the Pairwise Elo shift, and the Constitutional AI architecture.
2. [**Architecture & Vision**](docs/ARCHITECTURE.md): The technical breakdown of the 3-Tier Persona Architecture (Explicit Profiling -> Persona Classifier -> Persona Fingerprint Vector DB).
3. [**Calibration Guide**](docs/CALIBRATION_GUIDE.md): The exact rules and edge-cases for manually calibrating the Golden Dataset.
4. [**Solo Developer Roadmap**](docs/solo_developer_roadmap.md): The historical master plan for building and monetizing this platform as a solo dev.

## 🛠️ Project Structure
* `docs/`: The sole source of truth for project architecture.
* `data/`: Contains our JSON and JSONL datasets (e.g., `golden_dataset.json`, `arena_training_dataset.jsonl`).
* `scripts/`: Python scripts for automation, data ingestion, and the Constitutional AI simulator (`arena_bot.py`).
* `web/`: The Next.js frontend featuring the Radar Matrix UI and the A/B Arena.
* `inbox_evaluator/`: The core SDK.
