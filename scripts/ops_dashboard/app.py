"""
Ops visibility dashboard — local FastAPI aggregator.

  python3 scripts/ops_dashboard/app.py
  → http://127.0.0.1:8765
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from collectors import (
    collect_gcp_hardware,
    collect_gcp_pipeline,
    collect_mac_hardware,
    collect_mac_pipeline,
    collect_ollama,
    _latest_batch_empty,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
CACHE_TTL_SEC = float(os.getenv("OPS_DASHBOARD_CACHE_SEC", "4"))
HOST = os.getenv("OPS_DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("OPS_DASHBOARD_PORT", "8765"))

app = FastAPI(title="InboxEval Ops Dashboard", docs_url=None, redoc_url=None)

_cache_lock = threading.Lock()
_cache: dict = {"ts": 0.0, "payload": None}


def _snapshot_fresh() -> dict:
    """Collect Mac/GCP/hardware in parallel; never fails the whole payload."""
    results: dict = {}

    def run(name, fn):
        try:
            results[name] = fn()
        except Exception as e:
            results[name] = {"ok": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {
            pool.submit(run, "mac", collect_mac_pipeline): "mac",
            pool.submit(run, "gcp", collect_gcp_pipeline): "gcp",
            pool.submit(run, "hw_mac", collect_mac_hardware): "hw_mac",
            pool.submit(run, "hw_gcp", collect_gcp_hardware): "hw_gcp",
            pool.submit(run, "ollama", collect_ollama): "ollama",
        }
        for fut in as_completed(futs):
            fut.result()

    mac = results.get("mac") or {"ok": False}
    from datetime import datetime, timezone

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "title": "Golden Data Generator",
        "hero": mac.get("hero") if mac.get("ok") else None,
        "batch": mac.get("batch") if mac.get("ok") else _latest_batch_empty(),
        "mac": mac,
        "gcp": results.get("gcp") or {"ok": False},
        "hardware": {
            "mac": results.get("hw_mac") or {"ok": False},
            "gcp": results.get("hw_gcp") or {"ok": False},
            "secondary": results.get("ollama") or {"ok": False},
            # keep alias for older UI
            "ollama": results.get("ollama") or {"ok": False},
        },
    }


def get_cached_snapshot() -> dict:
    now = time.monotonic()
    with _cache_lock:
        if _cache["payload"] is not None and (now - _cache["ts"]) < CACHE_TTL_SEC:
            return _cache["payload"]
    payload = _snapshot_fresh()
    with _cache_lock:
        _cache["ts"] = time.monotonic()
        _cache["payload"] = payload
    return payload


@app.get("/api/snapshot")
def api_snapshot():
    return get_cached_snapshot()


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main():
    import uvicorn

    print(f"Ops dashboard → http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
