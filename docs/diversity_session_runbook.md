# Diversity session runbook

Operator checklist for one ~60-email non-micro harvest on the Mac, then delta-sync to GCP while Engine V4 keeps running.

---

## Prerequisites (once)

- venv active; `chromadb`, `sentence-transformers`, `eval_type_backport` installed
- `.env` has `GROQ_API_KEY*` (Step 01)
- Secondary laptop Ollama up (`OLLAMA_SECONDARY_LAPTOP_*` if non-default)
- GCP SSH / sync env ready only if you will sync

---

## Continuous Phase 1 (Mac)

One session is finite (~60 emails). For automatic claim → enrich → sync forever until the pool is empty:

1. Keep **Engine V4** running on GCP (tmux) — golden generation is separate.
2. On Mac, leave Ollama secondary up, then:

`./scripts/run_diversity_daemon.sh`

Optional: `SLEEP_SEC=30 ./scripts/run_diversity_daemon.sh` between rounds. Ctrl+C stops cleanly. Failed rounds retry after sleep; empty pool exits.

---

## One-shot (single batch)

1. Harvest only — `./scripts/run_diversity_session.sh`
2. Harvest + sync — `./scripts/run_diversity_session.sh --sync`
3. Reuse a batch — set `BATCH_ID`, then `./scripts/run_diversity_session.sh --reuse` (add `--sync` if needed)

Order inside a session: claim → Step 01 ∥ 02b → 02a → optional sync.

---

## What each stage does

| Stage | Role |
|--------|------|
| Claim | Stratified 30 short / 20 medium / 8 long / 2 massive → one `BATCH_ID` |
| Step 01 | Backtranslate via DynamicGroqRotator; writes `prompt` / `context` / `status` only |
| Step 02b | Chroma upsert for batch IDs (SQLite read-only) |
| Step 02a | Persona + DPBC in one UPDATE; waits on Chroma lock |
| Sync | Enrichment columns → GCP `raw_emails` where still `pending`; then Chroma |

---

## If something already finished mid-session

- Step 01+02b done, 02a failed → re-run only Step 02a with the same `BATCH_ID`
- All Mac enrichment done → dry-run sync, then real sync (`--verify`)
- Do **not** claim a new batch for the same emails; use `--reuse`

Current recoverable batch (first attempt): `0275e0fe51b8`.

---

## GCP sync vs Engine (no write collision)

- Sync uses `BEGIN IMMEDIATE` + `busy_timeout` so SQLite serializes with the Engine
- Updates only enrichment columns, and only rows still `status='pending'` (Engine-claimed rows are skipped)
- Never touches `golden_dataset`; count is checked before/after
- SQL first, then Chroma under flock

Safe while the GCP Engine VM is running. Never full-file rsync `pipeline.db`.

---

## Notes from first run

- OmniRoute is **not** used for Step 01 anymore (Groq rotator)
- Ollama Step 02a needs instructor `Mode.JSON` (already in script)
- Ctrl+C stops the Mac script; Ollama may keep the model in VRAM until keep-alive expires — unload on the secondary laptop if needed

---

## Dashboard

`./scripts/run_ops_dashboard.sh` → open `http://127.0.0.1:8765`  
Shows batch stages, Mac/GCP fleet + golden-by-size skew, Mac CPU/RAM, GCP **NVIDIA L4** (nvidia-smi), secondary **GTX 1050 4GB** (Ollama; util/temp/power only with SSH).

For live util/temp/power on the secondary GPU, enable SSH and set `SECONDARY_LAPTOP_SSH=user@192.168.0.8`. Defaults: `SECONDARY_GPU_NAME=NVIDIA GeForce GTX 1050`, `SECONDARY_GPU_VRAM_MB=4096`. Without SSH those sensors show **n/a** (not invented). GCP tok/s comes from vLLM `/metrics` counter deltas.
