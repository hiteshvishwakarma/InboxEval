"""Collectors for the local ops dashboard (Mac DB, GCP SSH, hardware)."""

from __future__ import annotations

import json
import logging
import os
import shlex
import sqlite3
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.request import urlopen

logger = logging.getLogger("OpsDashboard.collectors")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOCAL_DB = os.path.abspath(os.path.join(_ROOT, "data/pipeline.db"))
GCP_SSH_ALIAS = os.getenv("GCP_SSH_ALIAS", "inbox-engine")
GCP_DB_PATH = os.getenv("GCP_DB_PATH", "/home/hitesh/InboxEval/data/pipeline.db")
OLLAMA_BASE = os.getenv(
    "OLLAMA_SECONDARY_LAPTOP_BASE_URL", "http://192.168.0.8:11434"
).rstrip("/")
# Strip /v1 if present — /api/ps is on Ollama native root
if OLLAMA_BASE.endswith("/v1"):
    OLLAMA_BASE = OLLAMA_BASE[:-3].rstrip("/")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ssh_run(remote_cmd: str, timeout: float = 8.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", GCP_SSH_ALIAS, remote_cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ssh_python(script: str, timeout: float = 8.0) -> subprocess.CompletedProcess:
    remote = f"python3 -c {shlex.quote(script)}"
    return ssh_run(remote, timeout=timeout)


def collect_mac_pipeline(db_path: str = LOCAL_DB) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "error": None}
    if not os.path.exists(db_path):
        out["error"] = f"DB missing: {db_path}"
        return out
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA busy_timeout=10000")
        c = conn.cursor()

        status_rows = c.execute(
            "SELECT status, COUNT(*) FROM raw_emails GROUP BY status"
        ).fetchall()
        status = {str(s): int(n) for s, n in status_rows}

        total = sum(status.values())
        golden = 0
        try:
            golden = int(c.execute("SELECT COUNT(*) FROM golden_dataset").fetchone()[0])
        except sqlite3.OperationalError:
            pass

        non_micro = int(
            c.execute(
                "SELECT COUNT(*) FROM raw_emails WHERE size_category != 'micro'"
            ).fetchone()[0]
        )
        enriched = int(
            c.execute(
                """
                SELECT COUNT(*) FROM raw_emails
                WHERE size_category != 'micro'
                  AND prompt IS NOT NULL AND prompt != ''
                  AND target_persona IS NOT NULL
                  AND dpbc_targets IS NOT NULL
                """
            ).fetchone()[0]
        )
        pending_enrich = int(
            c.execute(
                """
                SELECT COUNT(*) FROM raw_emails
                WHERE size_category != 'micro'
                  AND status IN ('pending', 'backtranslated')
                  AND (dpbc_targets IS NULL
                       OR prompt IS NULL OR prompt = '')
                """
            ).fetchone()[0]
        )

        sync_backlog = 0
        synced = 0
        try:
            synced = int(c.execute("SELECT COUNT(*) FROM sync_log").fetchone()[0])
            sync_backlog = int(
                c.execute(
                    """
                    SELECT COUNT(*) FROM raw_emails r
                    WHERE r.size_category != 'micro'
                      AND r.prompt IS NOT NULL AND r.prompt != ''
                      AND r.target_persona IS NOT NULL
                      AND r.dpbc_targets IS NOT NULL
                      AND r.id NOT IN (SELECT raw_email_id FROM sync_log)
                    """
                ).fetchone()[0]
            )
        except sqlite3.OperationalError:
            pass

        batch = _latest_batch(conn)

        conn.close()
        out.update(
            {
                "ok": True,
                "total_raw": total,
                "status": status,
                "golden": golden,
                "non_micro": non_micro,
                "enriched_non_micro": enriched,
                "pending_enrichment": pending_enrich,
                "synced": synced,
                "sync_backlog": sync_backlog,
                "batch": batch,
            }
        )
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def _latest_batch(conn: sqlite3.Connection) -> Dict[str, Any]:
    empty = {
        "batch_id": None,
        "claimed": 0,
        "has_prompt": 0,
        "has_persona_dpbc": 0,
        "synced": 0,
        "current_stage": None,
        "stages": {},
    }
    try:
        row = conn.execute(
            """
            SELECT batch_id, COUNT(*) AS n, MAX(claimed_at) AS latest
            FROM diversity_batch
            GROUP BY batch_id
            ORDER BY latest DESC
            LIMIT 1
            """
        ).fetchone()
    except sqlite3.OperationalError:
        return empty
    if not row:
        return empty

    batch_id, claimed, _ = row[0], int(row[1]), row[2]
    stats = conn.execute(
        """
        SELECT
          SUM(CASE WHEN r.prompt IS NOT NULL AND r.prompt != '' THEN 1 ELSE 0 END),
          SUM(CASE WHEN r.target_persona IS NOT NULL AND r.dpbc_targets IS NOT NULL THEN 1 ELSE 0 END),
          SUM(CASE WHEN s.raw_email_id IS NOT NULL THEN 1 ELSE 0 END)
        FROM diversity_batch b
        JOIN raw_emails r ON r.id = b.raw_email_id
        LEFT JOIN sync_log s ON s.raw_email_id = r.id
        WHERE b.batch_id = ?
        """,
        (batch_id,),
    ).fetchone()
    has_prompt = int(stats[0] or 0)
    has_pd = int(stats[1] or 0)
    synced_n = int(stats[2] or 0)

    # step_02b proxy: prompts written (vectors usually done in parallel with 01)
    stages = {
        "claim": claimed,
        "step_01": has_prompt,
        "step_02b": has_prompt,  # proxy: vectorize scoped to same claimed IDs
        "step_02a": has_pd,
        "sync": synced_n,
    }
    current = "done"
    if has_prompt < claimed:
        current = "step_01"
    elif has_pd < claimed:
        current = "step_02a"
    elif synced_n < claimed:
        current = "sync"
    elif claimed > 0:
        current = "done"

    return {
        "batch_id": batch_id,
        "claimed": claimed,
        "has_prompt": has_prompt,
        "has_persona_dpbc": has_pd,
        "synced": synced_n,
        "current_stage": current,
        "stages": stages,
    }


def collect_gcp_pipeline() -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "error": None}
    script = f"""
import sqlite3, json
conn = sqlite3.connect({GCP_DB_PATH!r}, timeout=10)
c = conn.cursor()
status = {{str(k): int(v) for k, v in c.execute("SELECT status, COUNT(*) FROM raw_emails GROUP BY status").fetchall()}}
golden = c.execute("SELECT COUNT(*) FROM golden_dataset").fetchone()[0]
hourly = 0
try:
    hourly = c.execute(
        "SELECT COUNT(*) FROM golden_dataset WHERE created_at >= datetime('now', '-1 hour')"
    ).fetchone()[0]
except Exception:
    pass
enriched = c.execute('''
  SELECT COUNT(*) FROM raw_emails
  WHERE size_category != 'micro'
    AND prompt IS NOT NULL AND prompt != ''
    AND target_persona IS NOT NULL
    AND dpbc_targets IS NOT NULL
''').fetchone()[0]
pending = c.execute('''
  SELECT COUNT(*) FROM raw_emails
  WHERE size_category != 'micro' AND status = 'pending'
''').fetchone()[0]
print(json.dumps({{
  "status": status,
  "golden": golden,
  "golden_last_hour": hourly,
  "enriched_non_micro": enriched,
  "pending": pending,
}}))
conn.close()
"""
    try:
        result = ssh_python(script, timeout=10.0)
        if result.returncode != 0:
            out["error"] = (result.stderr or result.stdout or "ssh failed").strip()[:300]
            return out
        line = result.stdout.strip().splitlines()[-1]
        data = json.loads(line)
        out["ok"] = True
        out.update(data)
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def collect_mac_hardware() -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "error": None}
    try:
        import psutil

        vm = psutil.virtual_memory()
        out.update(
            {
                "ok": True,
                "cpu_pct": round(psutil.cpu_percent(interval=0.15), 1),
                "ram_used_gb": round(vm.used / (1024**3), 2),
                "ram_total_gb": round(vm.total / (1024**3), 2),
                "ram_pct": round(vm.percent, 1),
            }
        )
        temps = []
        try:
            sensors = psutil.sensors_temperatures() or {}
            for entries in sensors.values():
                for e in entries:
                    if e.current is not None:
                        temps.append(float(e.current))
        except Exception:
            pass
        if temps:
            out["temp_c"] = round(max(temps), 1)
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def collect_gcp_hardware() -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "error": None}
    cmd = (
        "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,"
        "temperature.gpu,power.draw --format=csv,noheader,nounits; "
        "free -m | awk '/Mem:/{printf \"RAM %s %s\\n\", $3, $2}'"
    )
    try:
        result = ssh_run(cmd, timeout=8.0)
        if result.returncode != 0:
            out["error"] = (result.stderr or "ssh failed").strip()[:300]
            return out
        lines = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
        gpu_line = next((ln for ln in lines if not ln.startswith("RAM")), None)
        ram_line = next((ln for ln in lines if ln.startswith("RAM")), None)
        if not gpu_line:
            out["error"] = "no nvidia-smi output"
            return out
        parts = [p.strip() for p in gpu_line.split(",")]
        out.update(
            {
                "ok": True,
                "gpu_util_pct": float(parts[0]),
                "gpu_vram_used_mb": float(parts[1]),
                "gpu_vram_total_mb": float(parts[2]),
                "gpu_temp_c": float(parts[3]),
                "gpu_power_w": float(parts[4]) if len(parts) > 4 else None,
            }
        )
        if ram_line:
            bits = ram_line.split()
            if len(bits) >= 3:
                used_mb, total_mb = float(bits[1]), float(bits[2])
                out["ram_used_gb"] = round(used_mb / 1024, 2)
                out["ram_total_gb"] = round(total_mb / 1024, 2)
                out["ram_pct"] = round(100.0 * used_mb / total_mb, 1) if total_mb else None
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def collect_ollama() -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "error": None, "models": []}
    url = f"{OLLAMA_BASE}/api/ps"
    try:
        with urlopen(url, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = []
        for m in data.get("models") or []:
            models.append(
                {
                    "name": m.get("name") or m.get("model"),
                    "size_vram": m.get("size_vram"),
                    "expires_at": m.get("expires_at"),
                }
            )
        out["ok"] = True
        out["models"] = models
        out["loaded"] = len(models) > 0
        return out
    except Exception as e:
        out["error"] = str(e)[:200]
        return out


def build_snapshot() -> Dict[str, Any]:
    mac = collect_mac_pipeline()
    return {
        "ts": _now(),
        "batch": mac.get("batch") if mac.get("ok") else _latest_batch_empty(),
        "mac": mac,
        "gcp": collect_gcp_pipeline(),
        "hardware": {
            "mac": collect_mac_hardware(),
            "gcp": collect_gcp_hardware(),
            "ollama": collect_ollama(),
        },
    }


def _latest_batch_empty() -> Dict[str, Any]:
    return {
        "batch_id": None,
        "claimed": 0,
        "has_prompt": 0,
        "has_persona_dpbc": 0,
        "synced": 0,
        "current_stage": None,
        "stages": {},
    }
