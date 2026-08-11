# Diversity session — ordered run commands

Use this as the operator checklist (and later wire the same order into the observability dashboard). Prefer running from your **own terminal**, not the Cursor agent.

**Current recoverable batch from first attempt:** `BATCH_ID=0275e0fe51b8` (60 claimed; Step 01 temporarily burned them to `failed` — reset before retry).

---

## 0) One-time / preflight

```bash
cd /Users/hiteshvishwakarma/Development/InboxEval
source venv/bin/activate

# Chroma + embeddings for Step 02b (required in venv)
pip install chromadb sentence-transformers

# OmniRoute must be up
curl -s http://localhost:20128/v1/models | head -c 200; echo

# Pick a working model id (step_01_combo is listed but returned 404/503 in our run).
# Examples that exist on this OmniRoute instance:
#   export OMNIROUTE_MODEL=auto/best-free
#   export OMNIROUTE_MODEL=groq/llama-3.3-70b-versatile
#   export OMNIROUTE_MODEL=step_01_combo   # only if combo backends are healthy
export OMNIROUTE_BASE_URL=http://localhost:20128/v1
export OMNIROUTE_API_KEY=omniroute
export OMNIROUTE_MODEL=auto/best-free

# Ollama for Step 02a (secondary laptop)
# export OLLAMA_SECONDARY_LAPTOP_BASE_URL=http://192.168.0.8:11434/v1
# export OLLAMA_SECONDARY_LAPTOP_MODEL=qwen2.5-coder:3b
```

Quick smoke test OmniRoute:

```bash
curl -s http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer omniroute" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$OMNIROUTE_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hi in 3 words\"}],\"max_tokens\":20}"
```

---

## 1) Claim batch (skip if reusing `0275e0fe51b8`)

```bash
python3 scripts/claim_diversity_batch.py
# copy BATCH_ID=...
export BATCH_ID=paste_here
```

### Reset a burned batch back to pending (do this for `0275e0fe51b8`)

```bash
export BATCH_ID=0275e0fe51b8
python3 - <<'PY'
import os, sqlite3
from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH
bid = os.environ["BATCH_ID"]
conn = sqlite3.connect(os.path.abspath(DB_PATH), timeout=30)
n = conn.execute("""
  UPDATE raw_emails SET status='pending', error_log=NULL
  WHERE id IN (SELECT raw_email_id FROM diversity_batch WHERE batch_id=?)
    AND (prompt IS NULL OR prompt='')
""", (bid,)).rowcount
conn.commit()
print(f"Reset {n} rows to pending for BATCH_ID={bid}")
conn.close()
PY
```

---

## 2) Step 01 — backtranslate (OmniRoute)

```bash
python3 scripts/data_pipeline/step_01_backtranslate.py --batch-id "$BATCH_ID"
```

---

## 3) Step 02b — vectorize (Chroma) — can run in parallel with Step 01

```bash
python3 scripts/data_pipeline/batch_vectorize.py --batch-id "$BATCH_ID"
```

Parallel form:

```bash
python3 scripts/data_pipeline/step_01_backtranslate.py --batch-id "$BATCH_ID" &
PID01=$!
python3 scripts/data_pipeline/batch_vectorize.py --batch-id "$BATCH_ID"
wait $PID01
```

---

## 4) Step 02a — persona + DPBC (Ollama) — after 02b preferred

```bash
python3 scripts/mass_horizontal_enrichment.py --batch-id "$BATCH_ID"
```

---

## 5) Sync to GCP (only when prompt+persona+dpbc ready)

```bash
python3 scripts/sync_delta_to_gcp.py --dry-run --batch-id "$BATCH_ID"
python3 scripts/sync_delta_to_gcp.py --verify --batch-id "$BATCH_ID"
```

---

## All-in-one (after preflight)

```bash
# Reuse existing batch after reset:
export BATCH_ID=0275e0fe51b8
# Or claim new: omit BATCH_ID and use ./scripts/run_diversity_session.sh

./scripts/run_diversity_session.sh          # harvest only
./scripts/run_diversity_session.sh --dry-sync
./scripts/run_diversity_session.sh --sync
```

Note: `run_diversity_session.sh` always **claims a new** batch. To retry `0275e0fe51b8`, run steps 2–5 manually with `BATCH_ID` set (do not claim again).

---

## What went wrong on the first run (reference)

1. **Claim OK** — 60 IDs under `0275e0fe51b8`.
2. **Step 02b crashed** — `ModuleNotFoundError: chromadb` in venv. Script `set -e` aborted the shell path, but Step 01 was already backgrounded.
3. **Step 01 OmniRoute** — `step_01_combo` returned **404** / **503** (combo listed but backends unhealthy). Old code marked all 60 as `status=failed`.
4. **Fix applied in code** — transient OmniRoute failures no longer set `failed`; rows stay retryable. Still **reset** this batch once (command above).

---

## Dashboard hook (later)

Poll Mac `data/pipeline.db` for:

```sql
-- per batch progress
SELECT b.batch_id, r.status,
  SUM(prompt IS NOT NULL AND prompt != '') AS has_prompt,
  SUM(target_persona IS NOT NULL) AS has_persona,
  SUM(dpbc_targets IS NOT NULL) AS has_dpbc,
  COUNT(*) AS n
FROM diversity_batch b
JOIN raw_emails r ON r.id = b.raw_email_id
GROUP BY b.batch_id, r.status;
```

Ordered stages for UI: `claim → step_01 → step_02b → step_02a → sync`.
