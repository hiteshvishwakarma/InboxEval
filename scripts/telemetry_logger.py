import os
import time
import json
import sqlite3
import subprocess
import argparse
from datetime import datetime, timezone

def get_gpu_metrics():
    try:
        cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv,noheader,nounits"
        out = subprocess.check_output(cmd, shell=True).decode('utf-8').strip().split(', ')
        return {
            "gpu_util_pct": float(out[0]),
            "gpu_vram_mb": float(out[1]),
            "gpu_temp_c": float(out[2]),
            "gpu_power_w": float(out[3])
        }
    except Exception as e:
        return {"gpu_error": str(e)}

def get_ram_metrics():
    try:
        with open('/proc/meminfo', 'r') as f:
            mem = f.readlines()
        total = int(mem[0].split()[1])
        available = int(mem[2].split()[1])
        return {"ram_used_gb": round((total - available) / 1024 / 1024, 2)}
    except Exception as e:
        return {"ram_error": str(e)}

def get_db_metrics(db_path):
    try:
        with sqlite3.connect(db_path) as c:
            golden = c.execute("SELECT COUNT(*) FROM golden_dataset").fetchone()[0]
            failed = c.execute("SELECT COUNT(*) FROM raw_emails WHERE status='failed'").fetchone()[0]
        return {"golden_count": golden, "failed_count": failed}
    except Exception as e:
        return {"db_error": str(e)}

def get_vllm_metrics(log_path):
    try:
        cmd = f"tail -n 200 {log_path} | grep 'Avg prompt throughput' | tail -n 1"
        out = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        return {"vllm_raw_log": out}
    except Exception as e:
        return {"vllm_raw_log": "No recent logs"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approach", required=True, help="Label for this A/B test run")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between logs")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    db_path = os.path.join(project_root, "data", "pipeline.db")
    log_path = os.path.join(project_root, "vllm_prod.log")
    out_file = os.path.join(project_root, "data", "ab_test_metrics.jsonl")

    print(f"Starting Zero-Overhead JSONL Logger for approach: {args.approach}")
    
    while True:
        try:
            record = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "approach": args.approach,
                **get_gpu_metrics(),
                **get_ram_metrics(),
                **get_db_metrics(db_path),
                **get_vllm_metrics(log_path)
            }
            
            with open(out_file, 'a') as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"Logger Error: {e}")
            
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
