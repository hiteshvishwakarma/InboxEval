"""
Shared helpers for stratified diversity session batches.

Table (Mac pipeline.db):
  diversity_batch(batch_id, raw_email_id PRIMARY KEY, size_category, claimed_at)
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_CATEGORIES: Tuple[str, ...] = ("short", "medium", "long", "massive")
DEFAULT_BATCH_PER_CATEGORY: Tuple[int, ...] = (30, 20, 8, 2)


def ensure_diversity_batch_table(conn: sqlite3.Connection) -> None:
    """Create diversity_batch if missing."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diversity_batch (
            batch_id TEXT NOT NULL,
            raw_email_id INTEGER PRIMARY KEY,
            size_category TEXT NOT NULL,
            claimed_at TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_diversity_batch_batch_id "
        "ON diversity_batch(batch_id)"
    )
    conn.commit()


def claim_stratified_batch(
    conn: sqlite3.Connection,
    categories: Sequence[str] = DEFAULT_CATEGORIES,
    batch_per_category: Sequence[int] = DEFAULT_BATCH_PER_CATEGORY,
    batch_id: Optional[str] = None,
) -> Tuple[str, List[Dict]]:
    """
    Claim pending emails stratified by size_category.

    Excludes IDs already present in diversity_batch. Returns (batch_id, rows).
    """
    if len(categories) != len(batch_per_category):
        raise ValueError("categories and batch_per_category length mismatch")

    ensure_diversity_batch_table(conn)
    batch_id = batch_id or uuid.uuid4().hex[:12]
    claimed_at = datetime.now(timezone.utc).isoformat()
    claimed: List[Dict] = []

    for cat, n in zip(categories, batch_per_category):
        if n <= 0:
            continue
        cursor = conn.execute(
            """
            SELECT id, size_category
            FROM raw_emails
            WHERE status = 'pending'
              AND size_category = ?
              AND id NOT IN (SELECT raw_email_id FROM diversity_batch)
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (cat, n),
        )
        for row in cursor.fetchall():
            email_id, size_category = row[0], row[1]
            conn.execute(
                """
                INSERT INTO diversity_batch(batch_id, raw_email_id, size_category, claimed_at)
                VALUES (?, ?, ?, ?)
                """,
                (batch_id, email_id, size_category, claimed_at),
            )
            claimed.append(
                {"id": email_id, "size_category": size_category, "batch_id": batch_id}
            )

    conn.commit()
    return batch_id, claimed


def get_batch_ids(conn: sqlite3.Connection, batch_id: str) -> List[int]:
    """Return raw_email_id list for a batch_id."""
    ensure_diversity_batch_table(conn)
    cursor = conn.execute(
        "SELECT raw_email_id FROM diversity_batch WHERE batch_id = ? ORDER BY raw_email_id",
        (batch_id,),
    )
    return [int(r[0]) for r in cursor.fetchall()]


def count_by_category(conn: sqlite3.Connection, batch_id: str) -> Dict[str, int]:
    """Return size_category -> count for a batch."""
    ensure_diversity_batch_table(conn)
    cursor = conn.execute(
        """
        SELECT size_category, COUNT(*)
        FROM diversity_batch
        WHERE batch_id = ?
        GROUP BY size_category
        """,
        (batch_id,),
    )
    return {str(cat): int(n) for cat, n in cursor.fetchall()}
