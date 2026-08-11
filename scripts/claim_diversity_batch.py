#!/usr/bin/env python3
"""
Claim a stratified diversity batch of pending non-micro emails.

Default quotas: short=30, medium=20, long=8, massive=2 (60 total).
Prints BATCH_ID for use by Step 01 / 02a / 02b / sync.

Usage:
  python3 scripts/claim_diversity_batch.py
  python3 scripts/claim_diversity_batch.py --categories short,medium --batch-per-category 30,20
"""

from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PIPELINE = os.path.join(_ROOT, "scripts", "data_pipeline")
sys.path.insert(0, _ROOT)
sys.path.insert(0, _PIPELINE)

from src.engine.golden_dataset_generator.db.pipeline_db import DB_PATH
from diversity_batch import (
    DEFAULT_BATCH_PER_CATEGORY,
    DEFAULT_CATEGORIES,
    claim_stratified_batch,
    count_by_category,
    ensure_diversity_batch_table,
)
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser(description="Claim stratified diversity batch")
    parser.add_argument(
        "--categories",
        default=",".join(DEFAULT_CATEGORIES),
        help="Comma-separated size categories (default excludes micro)",
    )
    parser.add_argument(
        "--batch-per-category",
        default=",".join(str(n) for n in DEFAULT_BATCH_PER_CATEGORY),
        help="Per-category limits matching --categories order",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional fixed batch_id (default: random 12-char hex)",
    )
    parser.add_argument(
        "--db-path",
        default=os.path.abspath(DB_PATH),
        help="Path to pipeline.db",
    )
    args = parser.parse_args()

    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    batches = [int(n.strip()) for n in args.batch_per_category.split(",")]
    if len(cats) != len(batches):
        print("ERROR: --categories and --batch-per-category must have the same length")
        sys.exit(1)

    if not os.path.exists(args.db_path):
        print(f"ERROR: DB not found: {args.db_path}")
        sys.exit(1)

    conn = sqlite3.connect(args.db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    ensure_diversity_batch_table(conn)

    batch_id, claimed = claim_stratified_batch(
        conn,
        categories=cats,
        batch_per_category=batches,
        batch_id=args.batch_id,
    )
    counts = count_by_category(conn, batch_id)
    conn.close()

    if not claimed:
        print("No pending emails claimed (pool empty or already claimed).")
        print(f"BATCH_ID={batch_id}")
        sys.exit(0)

    print(f"BATCH_ID={batch_id}")
    print(f"CLAIMED={len(claimed)}")
    print(f"COUNTS={counts}")
    print(f"SAMPLE_IDS={[r['id'] for r in claimed[:5]]}")


if __name__ == "__main__":
    main()
