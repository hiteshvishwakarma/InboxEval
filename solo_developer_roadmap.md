# Solo developer roadmap (architecture notes)

## 2026-08-11 — Parallel diversity harvest + delta GCP sync

**Decision:** Same claimed batch of ~60 non-micro emails for Step 01 (OmniRoute) and Steps 02a/02b (Ollama / Chroma), then delta-UPDATE to GCP while Engine V4 keeps running.

**Why not full DB rsync:** Would overwrite GCP `golden_dataset`. Sync only updates enrichment columns on `raw_emails` where `status='pending'`.

**Why not Redis:** SQLite column ownership + busy_timeout serializes Mac writers; Chroma uses flock wait/retry (`scripts/data_pipeline/chroma_lock.py`).

**Why not split 02a:** Persona+DPBC stay one UPDATE; splitting adds SQLite contention without quality gain. Order is 02b → 02a (Chroma write then read).

**Scripts:** `claim_diversity_batch.py`, `step_01_backtranslate.py`, `batch_vectorize.py`, `mass_horizontal_enrichment.py`, `sync_delta_to_gcp.py`. Runbook in `docs/implementation_plan_diversity_fix.md`.
