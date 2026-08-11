#!/usr/bin/env bash
# run_diversity_session.sh — one stratified ~60-email harvest session (Mac).
# Run this in YOUR terminal (not via the Cursor agent) so long LLM work
# does not burn agent tokens.
#
# Prerequisites:
#   - OmniRoute listening on :20128 (Step 01)
#   - Ollama on secondary laptop reachable (Step 02a)
#   - data/pipeline.db present
#   - For --sync: SSH alias inbox-engine works
#
# Usage:
#   ./scripts/run_diversity_session.sh
#   ./scripts/run_diversity_session.sh --sync
#   ./scripts/run_diversity_session.sh --dry-sync

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SYNC=0
DRY_SYNC=0
for arg in "$@"; do
  case "$arg" in
    --sync) SYNC=1 ;;
    --dry-sync) DRY_SYNC=1 ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
  esac
done

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

echo "==> Claim stratified batch (30/20/8/2)"
CLAIM_OUT="$(python3 scripts/claim_diversity_batch.py)"
echo "$CLAIM_OUT"
BATCH_ID="$(echo "$CLAIM_OUT" | awk -F= '/^BATCH_ID=/{print $2; exit}')"
if [[ -z "${BATCH_ID}" ]]; then
  echo "ERROR: could not parse BATCH_ID from claim output"
  exit 1
fi
export BATCH_ID
echo "Using BATCH_ID=$BATCH_ID"

echo "==> Step 01 (OmniRoute) + Step 02b (Chroma) in parallel"
python3 scripts/data_pipeline/step_01_backtranslate.py --batch-id "$BATCH_ID" &
PID01=$!
python3 scripts/data_pipeline/batch_vectorize.py --batch-id "$BATCH_ID"
wait "$PID01"
echo "Step 01 + 02b done."

echo "==> Step 02a (persona + DPBC; waits on Chroma lock if needed)"
python3 scripts/mass_horizontal_enrichment.py --batch-id "$BATCH_ID"
echo "Step 02a done."

if [[ "$DRY_SYNC" -eq 1 ]]; then
  echo "==> Dry-run sync (no SSH writes)"
  python3 scripts/sync_delta_to_gcp.py --dry-run --batch-id "$BATCH_ID"
elif [[ "$SYNC" -eq 1 ]]; then
  echo "==> Sync to GCP (--verify)"
  python3 scripts/sync_delta_to_gcp.py --verify --batch-id "$BATCH_ID"
else
  echo "==> Skipping GCP sync (pass --sync or --dry-sync when ready)"
fi

echo "Session complete. BATCH_ID=$BATCH_ID"
