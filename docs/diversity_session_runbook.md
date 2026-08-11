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

# Python 3.9 + instructor 1.x needs this for `str | Path` annotations
pip install eval_type_backport

# Step 01 uses DynamicGroqRotator (GROQ_API_KEY* in .env) — OmniRoute not required
python3 - <<'PY'
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path.cwd() / ".env")
from src.engine.golden_dataset_generator.utils.dynamic_groq_rotator import load_groq_api_keys
print(f"Groq keys loaded: {len(load_groq_api_keys())}")
PY

# Ollama for Step 02a (secondary laptop)
# export OLLAMA_SECONDARY_LAPTOP_BASE_URL=http://192.168.0.8:11434/v1
# export OLLAMA_SECONDARY_LAPTOP_MODEL=qwen2.5-coder:3b
```

Quick smoke test Groq rotator:

```bash
python3 - <<'PY'
import asyncio
from dotenv import load_dotenv
load_dotenv()
from src.engine.golden_dataset_generator.utils.dynamic_groq_rotator import get_default_rotator

async def main():
    r = get_default_rotator()
    data = await r.achat_completion(
        [{"role": "user", "content": "Reply with exactly: ok"}],
        max_tokens=16,
        temperature=0,
    )
    print(data.get("_rotator_model"), data["choices"][0]["message"]["content"][:80])

asyncio.run(main())
PY
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

## 2) Step 01 — backtranslate (DynamicGroqRotator)

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
BATCH_ID=$BATCH_ID ./scripts/run_diversity_session.sh --reuse

# Or claim new:
./scripts/run_diversity_session.sh          # harvest only
./scripts/run_diversity_session.sh --dry-sync
./scripts/run_diversity_session.sh --sync
```

---

## What went wrong on the first run (reference)

1. **Claim OK** — 60 IDs under `0275e0fe51b8`.
2. **Step 02b crashed** — `ModuleNotFoundError: chromadb` in venv. Script `set -e` aborted the shell path, but Step 01 was already backgrounded.
3. **Step 01 OmniRoute** — `step_01_combo` returned **404** / **503** (combo listed but backends unhealthy). Old code marked all 60 as `status=failed`.
4. **Fix** — Step 01 now uses **DynamicGroqRotator** (`GROQ_API_KEY*`); transient failures leave rows retryable. Reset batch once if still burned (command above).

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
