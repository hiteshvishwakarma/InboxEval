#!/usr/bin/env bash
# Local ops dashboard — Mac + GCP + Ollama snapshot UI.
#   ./scripts/run_ops_dashboard.sh
#   open http://127.0.0.1:8765

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

python3 -c "import fastapi, uvicorn, psutil" 2>/dev/null \
  || pip install fastapi uvicorn psutil

exec python3 scripts/ops_dashboard/app.py
