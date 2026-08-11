#!/usr/bin/env bash
# run_diversity_session.sh — one stratified ~60-email harvest session (Mac).
# Run in YOUR terminal (not Cursor agent) to avoid burning agent tokens.
#
# Usage:
#   ./scripts/run_diversity_session.sh
#   ./scripts/run_diversity_session.sh --sync
#   ./scripts/run_diversity_session.sh --dry-sync
#   BATCH_ID=0275e0fe51b8 ./scripts/run_diversity_session.sh --reuse
#
# Full ordered checklist: docs/diversity_session_runbook.md

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SYNC=0
DRY_SYNC=0
REUSE=0
for arg in "$@"; do
  case "$arg" in
    --sync) SYNC=1 ;;
    --dry-sync) DRY_SYNC=1 ;;
    --reuse) REUSE=1 ;;
    -h|--help)
      sed -n '1,25p' "$0"
      exit 0
      ;;
  esac
done

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

echo "==> Preflight"
python3 -c "import chromadb, sentence_transformers" 2>/dev/null \
  || { echo "ERROR: pip install chromadb sentence-transformers"; exit 1; }
curl -sf "http://localhost:20128/v1/models" >/dev/null \
  || { echo "ERROR: OmniRoute not reachable on :20128"; exit 1; }
echo "Preflight OK (chromadb + OmniRoute). Model=${OMNIROUTE_MODEL:-step_01_combo}"

if [[ "$REUSE" -eq 1 ]]; then
  if [[ -z "${BATCH_ID:-}" ]]; then
    echo "ERROR: --reuse requires BATCH_ID env var"
    exit 1
  fi
  echo "==> Reusing BATCH_ID=$BATCH_ID (no new claim)"
else
  echo "==> Claim stratified batch (30/20/8/2)"
  CLAIM_OUT="$(python3 scripts/claim_diversity_batch.py)"
  echo "$CLAIM_OUT"
  BATCH_ID="$(echo "$CLAIM_OUT" | awk -F= '/^BATCH_ID=/{print $2; exit}')"
  if [[ -z "${BATCH_ID}" ]]; then
    echo "ERROR: could not parse BATCH_ID from claim output"
    exit 1
  fi
  export BATCH_ID
fi
echo "Using BATCH_ID=$BATCH_ID"

cleanup_bg() {
  if [[ -n "${PID01:-}" ]] && kill -0 "$PID01" 2>/dev/null; then
    echo "Stopping background Step 01 (pid=$PID01)"
    kill "$PID01" 2>/dev/null || true
    wait "$PID01" 2>/dev/null || true
  fi
}
trap cleanup_bg EXIT

echo "==> Step 01 (OmniRoute) + Step 02b (Chroma) in parallel"
python3 scripts/data_pipeline/step_01_backtranslate.py --batch-id "$BATCH_ID" &
PID01=$!
set +e
python3 scripts/data_pipeline/batch_vectorize.py --batch-id "$BATCH_ID"
VEC_RC=$?
set -e
wait "$PID01" || true
PID01=""
if [[ "$VEC_RC" -ne 0 ]]; then
  echo "ERROR: Step 02b failed (rc=$VEC_RC). Fix deps then re-run with --reuse BATCH_ID=$BATCH_ID"
  exit "$VEC_RC"
fi
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

trap - EXIT
echo "Session complete. BATCH_ID=$BATCH_ID"
