#!/usr/bin/env bash
# run_diversity_daemon.sh — continuous Phase-1 harvest on Mac.
#
# Loops: claim 60 → Step 01 ∥ 02b → 02a → sync to GCP → next batch.
# Stops when the pending non-micro pool is empty (or Ctrl+C).
# Engine V4 on GCP is separate — keep it running in its own tmux.
#
# Usage (your terminal, not Cursor agent):
#   ./scripts/run_diversity_daemon.sh
#   SLEEP_SEC=30 ./scripts/run_diversity_daemon.sh
#
# Requires: Ollama secondary up, GROQ keys, ssh inbox-engine.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SLEEP_SEC="${SLEEP_SEC:-60}"
ROUND=0

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

echo "Diversity daemon starting (sleep ${SLEEP_SEC}s between rounds). Ctrl+C to stop."

while true; do
  ROUND=$((ROUND + 1))
  echo ""
  echo "======== DIVERSITY ROUND ${ROUND} $(date '+%Y-%m-%d %H:%M:%S') ========"

  set +e
  ./scripts/run_diversity_session.sh --sync
  RC=$?
  set -e

  if [[ "$RC" -eq 10 ]]; then
    echo "Pending non-micro pool empty after ${ROUND} round(s). Daemon exiting."
    exit 0
  fi
  if [[ "$RC" -ne 0 ]]; then
    echo "WARNING: round ${ROUND} failed (rc=${RC}). Sleeping ${SLEEP_SEC}s then retrying..."
    sleep "$SLEEP_SEC"
    continue
  fi

  echo "Round ${ROUND} OK. Sleeping ${SLEEP_SEC}s before next claim..."
  sleep "$SLEEP_SEC"
done
