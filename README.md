# InboxEval: AI Email Evaluator

InboxEval is an enterprise-grade benchmarking and evaluation platform designed to score AI-generated emails using advanced Persona-Driven grading methodologies.

## Documentation Navigation
To keep the project clean, all specialized documentation is organized in the `docs/` folder:

*   [**Solo Developer Roadmap**](docs/solo_developer_roadmap.md): The step-by-step master plan for building and monetizing this project.
*   [**AI Email Eval Framework**](docs/ai_email_eval_framework.md): The foundational product specification and system boundaries.
*   [**Architecture & Vision**](docs/ARCHITECTURE.md): The 3-Tier Persona Architecture (Explicit Profiling -> Persona Classifier -> Persona Fingerprint Vector DB).
*   [**Calibration & Grading Guide**](docs/CALIBRATION_GUIDE.md): The 12-Parameter matrix and the "Dynamic Persona-Driven Baseline" required for Golden Dataset calibration.

## Project Structure
*   `data/`: Contains our JSON datasets (including the manually calibrated `golden_dataset.json`).
*   `inbox_evaluator/`: The core Python SDK containing the static and dynamic Evaluator Engines.
*   `scripts/`: Automation scripts (like `prepare_golden_dataset.py`).

## Next Steps
(Currently in Phase 1: Engine Construction & Calibration)
