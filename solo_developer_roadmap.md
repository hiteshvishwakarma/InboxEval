# Solo developer roadmap (architecture notes)

## 2026-08-13 — Project parked (Engine V4 is not the product)

**Decision:** Stop treating InboxEval as a live golden-harvest. The vision (a SWE-bench-shaped metric for AI that writes / replies / acts-then-replies over email) is still open. The evolutionary Enron super-prompt loop is not that metric. Do not restart the L4 runner until there is a one-sentence oracle.

**What was actually achieved:** a working T-shaped pipeline (Mac enrichment + GCP vertical), ~497k sized Enron rows, 4,508 unique goldens merged locally, GPU occupancy, delta-sync without clobbering DBs, and a hard lesson: lock the eval object before scaling generation.

**Canonical keep:** `src/engine` + `engine_v2` + `engine_v3` + `engine_v4`, `tests/`, `docs/`, `data/pipeline.db`, `data/chroma_db`, `data/chroma_db_gcp`, `data/traces`, `data/gcp_engine_delta.db`.

**Decluttered (not in git):** split `data_chunk_*` / `data_part_*`, `data_backup.tar.gz`, empty stub `pipeline.db`s, superseded snapshots `pipeline_backup_gcp.db` and `pipeline_phase1_completed.db` (both 958 goldens), benchmark logs. Engine source and runners left in place.

**GCP:** instance halted (no L4 burn). Boot disk still bills until the VM is deleted in console.

## 2026-08-13 — Halt GCP Engine VM; merge goldens into Mac `pipeline.db`

**Why:** Stop L4 burn. Do **not** rsync-replace `data/pipeline.db` — Mac owns horizontal enrichment (`diversity_batch`, `sync_log`, extra `backtranslated`/dpbc) while GCP owned vertical Engine output.

**What stopped on `inbox-eval-engine`:** `mass_evolution_runner_v4.py` (SIGTERM), `vllm serve`, then `sudo shutdown -h now`. GPU was idle before halt.

**Conflict-safe merge (column ownership):**
- `golden_dataset`: insert GCP rows whose `raw_email_id` is missing locally (3549 new). Do not reuse GCP `id` — 17 PK collisions from local duplicate goldens on raw 346. Traces key by `raw_email_id`.
- `raw_emails.status`: apply GCP `completed` / `failed` only. Leave `locked_v4` as `backtranslated` (in-flight locks, engine dead). Never write GCP `pending` over Mac `backtranslated`.
- Enrichment (`prompt`/`persona`/`dpbc_targets`): **do not overwrite**. ~45k overlapping rows have *different* persona JSON (Mac vs GCP extractors). Fill only if local is empty (0 fills).
- Chroma: keep Mac `data/chroma_db` (313M > GCP 242M). GCP copy is `data/chroma_db_gcp`. Traces rsynced into `data/traces`. Delta snapshot: `data/gcp_engine_delta.db`.

**Post-merge local truth:** golden distinct raw **4508** (rows 4607 incl. historical dups), `completed` 4508, Mac dpbc/diversity tables preserved.

## 2026-08-12 — L4 GPU occupancy (max useful tok/s)

**Problem:** Runner `CONCURRENCY=15` × genesis `gather(5)` flooded vLLM (Running~6, Waiting~50), thrashing KV and failing long/massive on 8192.

**Fix:** `gpu_occupancy.py` — global LLM semaphore (6), email seat pool (4, size-weighted), admit gate on `vllm:num_requests_waiting`, size-aware genesis fan-out (5/4/3/2), head+tail email fit for context. Wired into runner + steps 05/06/08/10.

## 2026-08-12 — Engine V4 sampler must not fall back to micro

**Why diversification stalled:** Phase-1 Mac harvest correctly enriched non-micro rows, but `DiversitySampler.get_next_batch` only *preferred* the scarcest size, then filled the rest of each 100-wide batch with `size_category != target` — which included the huge `backtranslated` **micro** pool. Result: most Engine V4 goldens stayed micro; the skew radar barely moved.

**Fix:** V4 sampler eligible set is `short|medium|long|massive` only (`exclude_micro=True`). Deficit fill walks other non-micro categories by golden scarcity. Never claims micro in diversification mode. Redeploy sampler + restart `mass_evolution_runner_v4*` on GCP. Optional: unlock stranded `locked_v4` micros back to `backtranslated` if workers died mid-batch.

## 2026-08-11 — Parallel diversity harvest + delta GCP sync

**Decision:** Same claimed batch of ~60 non-micro emails for Step 01 (DynamicGroqRotator / `GROQ_API_KEY*`) and Steps 02a/02b (Ollama / Chroma), then delta-UPDATE to GCP while Engine V4 keeps running.

**Why not OmniRoute for Step 01:** `llm_client_factory` was OmniRoute/`OPENAI_BASE_URL` only (needed for Engine→vLLM on GCP). Diversity Step 01 now calls `dynamic_groq_rotator.py` directly. Factory keeps default OmniRoute/vLLM; set `LLM_BACKEND=groq` for instructor Groq rotation.

**Why not full DB rsync:** Would overwrite GCP `golden_dataset`. Sync only updates enrichment columns on `raw_emails` where `status='pending'`.

**Why not Redis:** SQLite column ownership + busy_timeout serializes Mac writers; Chroma uses flock wait/retry (`scripts/data_pipeline/chroma_lock.py`).

**Why not split 02a:** Persona+DPBC stay one UPDATE; splitting adds SQLite contention without quality gain. Order is 02b → 02a (Chroma write then read).

**Scripts:** `claim_diversity_batch.py`, `step_01_backtranslate.py`, `batch_vectorize.py`, `mass_horizontal_enrichment.py`, `sync_delta_to_gcp.py`, `run_diversity_daemon.sh`, `run_ops_dashboard.sh`. Runbook: `docs/diversity_session_runbook.md`.

**Ops dashboard:** Local FastAPI at `:8765` — latest diversity batch stages, Mac vs GCP pipeline counts, Mac CPU/RAM + GCP GPU (SSH) + Ollama `/api/ps` (best-effort).
