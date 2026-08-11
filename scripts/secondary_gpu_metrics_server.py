#!/usr/bin/env python3
"""
Tiny GPU metrics HTTP exporter for the secondary laptop (Ollama host).

Run ON the secondary machine (not Mac):
  python3 secondary_gpu_metrics_server.py
  # serves http://0.0.0.0:9191/gpu.json

Mac dashboard auto-probes http://<OLLAMA_HOST>:9191/gpu.json
No SSH required.

Requires: nvidia-smi on PATH.
"""

from __future__ import annotations

import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


PORT = 9191


def read_gpu() -> dict:
    cmd = (
        "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,"
        "temperature.gpu,power.draw --format=csv,noheader,nounits"
    )
    out = subprocess.check_output(cmd, shell=True, text=True).strip().splitlines()[0]
    parts = [p.strip() for p in out.split(",")]
    data = {
        "gpu_name": parts[0],
        "gpu_util_pct": float(parts[1]),
        "gpu_vram_used_mb": float(parts[2]),
        "gpu_vram_total_mb": float(parts[3]),
        "gpu_temp_c": float(parts[4]),
        "gpu_power_w": float(parts[5]) if len(parts) > 5 and parts[5] not in ("[N/A]", "N/A") else None,
    }
    try:
        free = subprocess.check_output(
            "free -m | awk '/Mem:/{print $3,$2}'", shell=True, text=True
        ).split()
        used_mb, total_mb = float(free[0]), float(free[1])
        data["ram_used_gb"] = round(used_mb / 1024, 2)
        data["ram_total_gb"] = round(total_mb / 1024, 2)
        data["ram_pct"] = round(100.0 * used_mb / total_mb, 1)
    except Exception:
        pass
    return data


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/gpu.json", "/"):
            self.send_response(404)
            self.end_headers()
            return
        try:
            payload = json.dumps(read_gpu()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:
            err = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    print(f"Secondary GPU metrics → http://0.0.0.0:{PORT}/gpu.json")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
