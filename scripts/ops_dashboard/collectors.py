"""Collectors for the local ops dashboard (Mac DB, GCP SSH, secondary GPU)."""

from __future__ import annotations

import json
import logging
import os
import shlex
import sqlite3
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import urlopen

logger = logging.getLogger("OpsDashboard.collectors")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOCAL_DB = os.path.abspath(os.path.join(_ROOT, "data/pipeline.db"))
GCP_SSH_ALIAS = os.getenv("GCP_SSH_ALIAS", "inbox-engine")
GCP_DB_PATH = os.getenv("GCP_DB_PATH", "/home/hitesh/InboxEval/data/pipeline.db")
OLLAMA_BASE = os.getenv(
    "OLLAMA_SECONDARY_LAPTOP_BASE_URL", "http://192.168.0.8:11434"
).rstrip("/")
if OLLAMA_BASE.endswith("/v1"):
    OLLAMA_BASE = OLLAMA_BASE[:-3].rstrip("/")

# Secondary laptop GPU (Ollama host) — full nvidia-smi needs SSH.
# Defaults match operator hardware: GeForce GTX 1050 4GB (not invented at runtime).
SECONDARY_SSH = os.getenv("SECONDARY_LAPTOP_SSH", "").strip()
SECONDARY_GPU_NAME = os.getenv("SECONDARY_GPU_NAME", "NVIDIA GeForce GTX 1050")
SECONDARY_GPU_VRAM_MB = float(os.getenv("SECONDARY_GPU_VRAM_MB", "4096"))

# vLLM tok/s derived from counter deltas (factual), not invented.
_vllm_tok_lock = __import__("threading").Lock()
_vllm_tok_prev: Dict[str, float] = {"t": 0.0, "gen": 0.0, "prompt": 0.0}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ssh_run(
    remote_cmd: str,
    *,
    host: Optional[str] = None,
    timeout: float = 8.0,
) -> subprocess.CompletedProcess:
    target = host or GCP_SSH_ALIAS
    return subprocess.run(
        [
            "ssh",
            "-o",
            "ConnectTimeout=4",
            "-o",
            "BatchMode=yes",
            target,
            remote_cmd,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ssh_python(script: str, timeout: float = 8.0) -> subprocess.CompletedProcess:
    remote = f"python3 -c {shlex.quote(script)}"
    return ssh_run(remote, timeout=timeout)


def _golden_skew(conn: sqlite3.Connection) -> Dict[str, int]:
    try:
        rows = conn.execute(
            """
            SELECT COALESCE(r.size_category, 'unknown'), COUNT(*)
            FROM golden_dataset g
            JOIN raw_emails r ON r.id = g.raw_email_id
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
        return {str(cat): int(n) for cat, n in rows}
    except sqlite3.OperationalError:
        return {}


def _batch_stats(conn: sqlite3.Connection, batch_id: str) -> Dict[str, Any]:
    claimed = int(
        conn.execute(
            "SELECT COUNT(*) FROM diversity_batch WHERE batch_id=?", (batch_id,)
        ).fetchone()[0]
    )
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
    stages = {
        "claim": claimed,
        "step_01": has_prompt,
        "step_02b": has_prompt,
        "step_02a": has_pd,
        "sync": synced_n,
    }
    if has_prompt < claimed:
        current = "step_01"
    elif has_pd < claimed:
        current = "step_02a"
    elif synced_n < claimed:
        current = "sync"
    else:
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


def _detect_local_worker(batch_id: Optional[str]) -> Dict[str, Any]:
    """True when mass_horizontal / step_01 for this batch is still running."""
    info = {"enriching": False, "pid": None, "cmdline": None}
    try:
        import psutil

        for proc in psutil.process_iter(["pid", "cmdline"]):
            cmd = " ".join(proc.info.get("cmdline") or [])
            if "mass_horizontal_enrichment.py" in cmd or "step_01_backtranslate.py" in cmd:
                if batch_id and batch_id in cmd:
                    info = {"enriching": True, "pid": proc.info["pid"], "cmdline": cmd[-120:]}
                    break
                if not batch_id and ("mass_horizontal" in cmd or "step_01" in cmd):
                    info = {"enriching": True, "pid": proc.info["pid"], "cmdline": cmd[-120:]}
    except Exception:
        pass
    return info


def _latest_batch(conn: sqlite3.Connection) -> Dict[str, Any]:
    empty = {
        "batch_id": None,
        "claimed": 0,
        "has_prompt": 0,
        "has_persona_dpbc": 0,
        "synced": 0,
        "current_stage": None,
        "stages": {},
        "note": None,
        "worker": {"enriching": False},
    }
    try:
        rows = conn.execute(
            """
            SELECT batch_id, MAX(claimed_at) AS latest
            FROM diversity_batch
            GROUP BY batch_id
            ORDER BY latest DESC
            LIMIT 8
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return empty
    if not rows:
        return empty

    # Prefer newest incomplete batch (persona/dpbc or sync remaining)
    chosen = None
    for batch_id, _ in rows:
        stats = _batch_stats(conn, batch_id)
        if stats["current_stage"] != "done":
            chosen = stats
            break
    if chosen is None:
        chosen = _batch_stats(conn, rows[0][0])

    worker = _detect_local_worker(chosen.get("batch_id"))
    chosen["worker"] = worker
    # Step 02a writes after the full chunk — 0/60 with worker live is expected
    if (
        chosen.get("current_stage") == "step_02a"
        and chosen.get("has_persona_dpbc", 0) == 0
        and worker.get("enriching")
    ):
        chosen["note"] = (
            "Step 02a extracts all personas first, then writes — "
            "counter stays 0/N until the chunk finishes (not stuck)."
        )
    elif chosen.get("current_stage") == "step_02a" and worker.get("enriching"):
        chosen["note"] = "Step 02a worker running."
    return chosen


def collect_mac_pipeline(db_path: str = LOCAL_DB) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "error": None}
    if not os.path.exists(db_path):
        out["error"] = f"DB missing: {db_path}"
        return out
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA busy_timeout=10000")
        c = conn.cursor()

        status = {
            str(s): int(n)
            for s, n in c.execute(
                "SELECT status, COUNT(*) FROM raw_emails GROUP BY status"
            ).fetchall()
        }
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

        skew = _golden_skew(conn)
        email_by_size = {
            str(cat): int(n)
            for cat, n in c.execute(
                "SELECT size_category, COUNT(*) FROM raw_emails GROUP BY size_category"
            ).fetchall()
        }
        backtranslated = int(
            c.execute(
                "SELECT COUNT(*) FROM raw_emails WHERE prompt IS NOT NULL AND prompt != ''"
            ).fetchone()[0]
        )
        persona_n = int(
            c.execute(
                "SELECT COUNT(*) FROM raw_emails WHERE target_persona IS NOT NULL"
            ).fetchone()[0]
        )
        dpbc_n = int(
            c.execute(
                "SELECT COUNT(*) FROM raw_emails WHERE dpbc_targets IS NOT NULL"
            ).fetchone()[0]
        )
        vectorized = _chroma_vector_count()
        batch = _latest_batch(conn)
        # Per-size: corpus vs golden (factual joins)
        size_rows = []
        for cat in ("micro", "short", "medium", "long", "massive"):
            size_rows.append(
                {
                    "size": cat,
                    "emails": email_by_size.get(cat, 0),
                    "golden": skew.get(cat, 0),
                }
            )
        for cat, n in email_by_size.items():
            if cat not in ("micro", "short", "medium", "long", "massive"):
                size_rows.append({"size": cat, "emails": n, "golden": skew.get(cat, 0)})

        conn.close()
        out.update(
            {
                "ok": True,
                "total_raw": total,
                "status": status,
                "golden": golden,
                "golden_by_size": skew,
                "email_by_size": email_by_size,
                "size_breakdown": size_rows,
                "backtranslated": backtranslated,
                "persona_extracted": persona_n,
                "dpbc_extracted": dpbc_n,
                "vectorized": vectorized,
                "non_micro": non_micro,
                "enriched_non_micro": enriched,
                "pending_enrichment": pending_enrich,
                "synced": synced,
                "sync_backlog": sync_backlog,
                "batch": batch,
                "hero": {
                    "title": "Golden Data Generator",
                    "total_emails": total,
                    "golden": golden,
                    "backtranslated": backtranslated,
                    "persona_extracted": persona_n,
                    "dpbc_extracted": dpbc_n,
                    "vectorized": vectorized,
                    "size_breakdown": size_rows,
                },
            }
        )
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def _chroma_vector_count() -> Optional[int]:
    """Count vectors in local Chroma inbox_eval_vectors (factual)."""
    try:
        import chromadb

        path = os.path.abspath(os.path.join(_ROOT, "data/chroma_db"))
        if not os.path.isdir(path):
            return None
        client = chromadb.PersistentClient(path=path)
        for col in client.list_collections():
            if col.name == "inbox_eval_vectors":
                return int(col.count())
        # fallback: largest collection
        counts = [int(c.count()) for c in client.list_collections()]
        return max(counts) if counts else None
    except Exception:
        return None


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
skew = {{}}
try:
    skew = {{str(cat): int(n) for cat, n in c.execute('''
      SELECT COALESCE(r.size_category, 'unknown'), COUNT(*)
      FROM golden_dataset g JOIN raw_emails r ON r.id = g.raw_email_id
      GROUP BY 1 ORDER BY 1
    ''').fetchall()}}
except Exception:
    pass
print(json.dumps({{
  "status": status,
  "golden": golden,
  "golden_last_hour": hourly,
  "golden_by_size": skew,
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
    out: Dict[str, Any] = {
        "ok": False,
        "error": None,
        "role": "Mac · Step 01 (Groq API)",
        "label": "MacBook Pro",
        "gpu_name": None,
        "models": [{"name": "GROQ_API_KEY* rotator (cloud)"}],
        "tokens_per_sec": None,
        "tokens_per_sec_note": "n/a — Groq is remote; no local tok/s counter",
        "metrics_source": "psutil",
    }
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


def _parse_nvidia_smi(stdout: str) -> Dict[str, Any]:
    """Parse: name, util, mem_used, mem_total, temp, power then optional RAM line."""
    out: Dict[str, Any] = {}
    lines = [ln.strip() for ln in stdout.strip().splitlines() if ln.strip()]
    gpu_line = next((ln for ln in lines if not ln.startswith("RAM")), None)
    ram_line = next((ln for ln in lines if ln.startswith("RAM")), None)
    if not gpu_line:
        raise ValueError("no nvidia-smi gpu line")
    parts = [p.strip() for p in gpu_line.split(",")]
    # with name: 6 fields; without: 5
    if len(parts) >= 6:
        out["gpu_name"] = parts[0]
        out["gpu_util_pct"] = float(parts[1])
        out["gpu_vram_used_mb"] = float(parts[2])
        out["gpu_vram_total_mb"] = float(parts[3])
        out["gpu_temp_c"] = float(parts[4])
        try:
            out["gpu_power_w"] = float(parts[5])
        except ValueError:
            out["gpu_power_w"] = None
    else:
        out["gpu_util_pct"] = float(parts[0])
        out["gpu_vram_used_mb"] = float(parts[1])
        out["gpu_vram_total_mb"] = float(parts[2])
        out["gpu_temp_c"] = float(parts[3])
        out["gpu_power_w"] = float(parts[4]) if len(parts) > 4 else None
    if ram_line:
        bits = ram_line.split()
        if len(bits) >= 3:
            used_mb, total_mb = float(bits[1]), float(bits[2])
            out["ram_used_gb"] = round(used_mb / 1024, 2)
            out["ram_total_gb"] = round(total_mb / 1024, 2)
            out["ram_pct"] = round(100.0 * used_mb / total_mb, 1) if total_mb else None
    return out


_NVIDIA_QUERY = (
    "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,"
    "temperature.gpu,power.draw --format=csv,noheader,nounits; "
    "free -m | awk '/Mem:/{printf \"RAM %s %s\\n\", $3, $2}'"
)


def collect_vllm_throughput() -> Dict[str, Any]:
    """
    Factual tok/s from vLLM /metrics counter deltas on GCP.
    Returns null rates until a second sample exists.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "model": None,
        "tokens_per_sec": None,
        "prompt_tokens_per_sec": None,
        "generation_tokens_total": None,
        "requests_running": None,
    }
    cmd = (
        "curl -s --max-time 2 http://127.0.0.1:8000/metrics 2>/dev/null | "
        "grep -E '^vllm:(generation_tokens_total|prompt_tokens_total|num_requests_running)\\{' "
        "| head -20"
    )
    try:
        result = ssh_run(cmd, timeout=8.0)
        if result.returncode != 0 or not result.stdout.strip():
            out["error"] = "vLLM /metrics unreachable"
            return out
        import re
        import time as _time

        gen = None
        prompt = None
        running = None
        model = None
        for line in result.stdout.splitlines():
            m = re.search(r'model_name="([^"]+)"', line)
            if m:
                model = m.group(1)
            if line.startswith("vllm:generation_tokens_total"):
                gen = float(line.rsplit(" ", 1)[-1])
            elif line.startswith("vllm:prompt_tokens_total{"):
                prompt = float(line.rsplit(" ", 1)[-1])
            elif line.startswith("vllm:num_requests_running"):
                running = float(line.rsplit(" ", 1)[-1])
        now = _time.monotonic()
        out.update(
            {
                "ok": True,
                "model": model,
                "generation_tokens_total": gen,
                "prompt_tokens_total": prompt,
                "requests_running": running,
            }
        )
        with _vllm_tok_lock:
            prev_t = _vllm_tok_prev["t"]
            prev_g = _vllm_tok_prev["gen"]
            prev_p = _vllm_tok_prev["prompt"]
            if prev_t > 0 and gen is not None and now > prev_t:
                dt = now - prev_t
                out["tokens_per_sec"] = round((gen - prev_g) / dt, 1)
                if prompt is not None:
                    out["prompt_tokens_per_sec"] = round((prompt - prev_p) / dt, 1)
            if gen is not None:
                _vllm_tok_prev["t"] = now
                _vllm_tok_prev["gen"] = gen
                if prompt is not None:
                    _vllm_tok_prev["prompt"] = prompt
        if out["tokens_per_sec"] is None:
            out["tokens_per_sec_note"] = "warming — need 2 samples (~5s)"
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def collect_gcp_hardware() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "ok": False,
        "error": None,
        "role": "GCP · Engine V4 (vLLM)",
        "label": "GCP Engine GPU",
        "metrics_source": "nvidia-smi",
    }
    try:
        result = ssh_run(_NVIDIA_QUERY, timeout=8.0)
        if result.returncode != 0:
            out["error"] = (result.stderr or "ssh failed").strip()[:300]
            return out
        parsed = _parse_nvidia_smi(result.stdout)
        out["ok"] = True
        out.update(parsed)
        name = parsed.get("gpu_name") or "NVIDIA GPU"
        vram_gb = round(parsed.get("gpu_vram_total_mb", 0) / 1024, 1)
        out["label"] = f"{name} · {vram_gb} GB"
        out["gpu_name"] = name
        # Attach vLLM model + tok/s (factual deltas)
        vllm = collect_vllm_throughput()
        out["vllm"] = vllm
        if vllm.get("model"):
            out["models"] = [{"name": vllm["model"]}]
        out["tokens_per_sec"] = vllm.get("tokens_per_sec")
        out["tokens_per_sec_note"] = vllm.get("tokens_per_sec_note")
        out["prompt_tokens_per_sec"] = vllm.get("prompt_tokens_per_sec")
        out["requests_running"] = vllm.get("requests_running")
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


def _ollama_ps() -> Dict[str, Any]:
    url = f"{OLLAMA_BASE}/api/ps"
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
    return {"ok": True, "models": models, "loaded": len(models) > 0}


def collect_secondary_hardware() -> Dict[str, Any]:
    """
    Secondary laptop GPU (Ollama). nvidia-smi only when SECONDARY_LAPTOP_SSH works.
    Without SSH: configured GTX 1050 4GB name + factual Ollama model VRAM only.
    Never invents util/temp/power.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "error": None,
        "role": "Secondary · Step 02a (Ollama)",
        "label": SECONDARY_GPU_NAME,
        "gpu_name": SECONDARY_GPU_NAME,
        "gpu_vram_total_mb": SECONDARY_GPU_VRAM_MB,
        "models": [],
        "metrics_source": None,
        "tokens_per_sec": None,
        "tokens_per_sec_note": "n/a — Ollama /api/ps does not expose tok/s",
    }
    try:
        ps = _ollama_ps()
        out["models"] = ps["models"]
        out["loaded"] = ps["loaded"]
        out["ollama_ok"] = True
        if ps["models"] and ps["models"][0].get("size_vram"):
            out["gpu_vram_used_mb"] = round(
                ps["models"][0]["size_vram"] / (1024 * 1024), 1
            )
    except Exception as e:
        out["ollama_ok"] = False
        out["ollama_error"] = str(e)[:160]

    ssh_host = SECONDARY_SSH
    if not ssh_host:
        host = urlparse(OLLAMA_BASE).hostname
        user = os.getenv("SECONDARY_LAPTOP_SSH_USER", "").strip()
        if host and user:
            ssh_host = f"{user}@{host}"

    if ssh_host:
        try:
            result = ssh_run(_NVIDIA_QUERY, host=ssh_host, timeout=6.0)
            if result.returncode == 0 and result.stdout.strip():
                parsed = _parse_nvidia_smi(result.stdout)
                out.update(parsed)
                out["metrics_source"] = "nvidia-smi"
                name = parsed.get("gpu_name") or SECONDARY_GPU_NAME
                vram_gb = round(parsed.get("gpu_vram_total_mb", 0) / 1024, 1)
                out["label"] = f"{name} · {vram_gb} GB"
                out["gpu_name"] = name
                out["ok"] = True
                out["note"] = None
                return out
            out["ssh_error"] = (result.stderr or "ssh failed").strip()[:200]
        except Exception as e:
            out["ssh_error"] = str(e)[:200]

    vram_gb = round(SECONDARY_GPU_VRAM_MB / 1024, 1)
    out["label"] = f"{SECONDARY_GPU_NAME} · {vram_gb} GB"
    out["metrics_source"] = "config+ollama"
    # Explicitly omit inventing zeros — UI must show n/a
    out.pop("gpu_util_pct", None)
    out.pop("gpu_temp_c", None)
    out.pop("gpu_power_w", None)
    out["gpu_util_pct"] = None
    out["gpu_temp_c"] = None
    out["gpu_power_w"] = None
    if out.get("ollama_ok"):
        out["ok"] = True
        out["note"] = (
            "util/temp/power unavailable — enable SSH "
            "(SECONDARY_LAPTOP_SSH=user@host). "
            "VRAM used is from Ollama; total 4GB is configured for GTX 1050."
        )
    else:
        out["error"] = out.get("ollama_error") or out.get("ssh_error") or "unreachable"
    return out


# Back-compat alias used by app.py
collect_ollama = collect_secondary_hardware


def _latest_batch_empty() -> Dict[str, Any]:
    return {
        "batch_id": None,
        "claimed": 0,
        "has_prompt": 0,
        "has_persona_dpbc": 0,
        "synced": 0,
        "current_stage": None,
        "stages": {},
        "note": None,
        "worker": {"enriching": False},
    }
