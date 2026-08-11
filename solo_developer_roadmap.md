# Solo developer roadmap (architecture notes)

## 2026-08-11 — Parallel diversity harvest + delta GCP sync

**Decision:** Same claimed batch of ~60 non-micro emails for Step 01 (DynamicGroqRotator / `GROQ_API_KEY*`) and Steps 02a/02b (Ollama / Chroma), then delta-UPDATE to GCP while Engine V4 keeps running.

**Why not OmniRoute for Step 01:** `llm_client_factory` was OmniRoute/`OPENAI_BASE_URL` only (needed for Engine→vLLM on GCP). Diversity Step 01 now calls `dynamic_groq_rotator.py` directly. Factory keeps default OmniRoute/vLLM; set `LLM_BACKEND=groq` for instructor Groq rotation.

**Why not full DB rsync:** Would overwrite GCP `golden_dataset`. Sync only updates enrichment columns on `raw_emails` where `status='pending'`.

**Why not Redis:** SQLite column ownership + busy_timeout serializes Mac writers; Chroma uses flock wait/retry (`scripts/data_pipeline/chroma_lock.py`).

**Why not split 02a:** Persona+DPBC stay one UPDATE; splitting adds SQLite contention without quality gain. Order is 02b → 02a (Chroma write then read).

**Scripts:** `claim_diversity_batch.py`, `step_01_backtranslate.py`, `batch_vectorize.py`, `mass_horizontal_enrichment.py`, `sync_delta_to_gcp.py`, `run_diversity_daemon.sh`, `run_ops_dashboard.sh`. Runbook: `docs/diversity_session_runbook.md`.

**Ops dashboard:** Local FastAPI at `:8765` — latest diversity batch stages, Mac vs GCP pipeline counts, Mac CPU/RAM + GCP GPU (SSH) + Ollama `/api/ps` (best-effort).
