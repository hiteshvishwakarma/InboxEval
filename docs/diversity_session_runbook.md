# Diversity session runbook

Operator checklist for one ~60-email non-micro harvest on the Mac, then delta-sync to GCP while Engine V4 keeps running.

---

## Prerequisites (once)

- venv active; `chromadb`, `sentence-transformers`, `eval_type_backport` installed
- `.env` has `GROQ_API_KEY*` (Step 01)
- Secondary laptop Ollama up (`OLLAMA_SECONDARY_LAPTOP_*` if non-default)
- GCP SSH / sync env ready only if you will sync

---

## Normal path (one command)

Prefer this over running steps by hand.

1. **New batch + harvest only** — `./scripts/run_diversity_session.sh`
2. **New batch + dry-run sync** — `./scripts/run_diversity_session.sh --dry-sync`
3. **New batch + real sync** — `./scripts/run_diversity_session.sh --sync`
4. **Reuse an existing batch** — set `BATCH_ID`, then `./scripts/run_diversity_session.sh --reuse` (add `--sync` / `--dry-sync` when ready)

That script, in order: claim (unless `--reuse`) → Step 01 ∥ Step 02b → Step 02a → optional GCP sync.

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

## Later: dashboard

UI stages in order: `claim → step_01 → step_02b → step_02a → sync` (poll Mac `pipeline.db` per `BATCH_ID`).
