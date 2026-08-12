"""Unit tests for Engine V4 DiversitySampler (no micro fallback)."""

import sqlite3
from pathlib import Path

from src.engine_v4.golden_dataset_generator_v4.diversity_sampler import DiversitySampler


def _setup_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE raw_emails (
            id INTEGER PRIMARY KEY,
            raw_text TEXT,
            target_persona TEXT,
            dpbc_targets TEXT,
            size_category TEXT,
            status TEXT
        );
        CREATE TABLE golden_dataset (
            id INTEGER PRIMARY KEY,
            raw_email_id INTEGER
        );
        """
    )
    # Golden already skewed to micro
    for i in range(1, 21):
        conn.execute(
            "INSERT INTO raw_emails VALUES (?,?,?,?,?,?)",
            (i, f"micro-{i}", "{}", "{}", "micro", "completed"),
        )
        conn.execute("INSERT INTO golden_dataset VALUES (?,?)", (i, i))

    # Ready non-micro pool
    ready = [
        (100, "short", "backtranslated"),
        (101, "short", "backtranslated"),
        (102, "medium", "backtranslated"),
        (103, "long", "backtranslated"),
        (104, "massive", "backtranslated"),
        # Micro ready — must NEVER be claimed in diversification mode
        (200, "micro", "backtranslated"),
        (201, "micro", "backtranslated"),
        (202, "micro", "backtranslated"),
    ]
    for eid, cat, status in ready:
        conn.execute(
            "INSERT INTO raw_emails VALUES (?,?,?,?,?,?)",
            (eid, f"text-{eid}", '{"p":1}', '{"d":1}', cat, status),
        )
    # One massive already golden → massive least? actually golden: micro=20, others=0
    # except we add one medium golden so order is clear
    conn.execute(
        "INSERT INTO raw_emails VALUES (?,?,?,?,?,?)",
        (50, "med-done", "{}", "{}", "medium", "completed"),
    )
    conn.execute("INSERT INTO golden_dataset VALUES (?,?)", (50, 50))
    conn.commit()
    conn.close()


def test_never_claims_micro(tmp_path: Path):
    db = tmp_path / "t.db"
    _setup_db(db)
    sampler = DiversitySampler(str(db), exclude_micro=True)
    batch = sampler.get_next_batch(10)
    assert batch, "expected non-micro claims"
    assert all(
        sqlite3.connect(db)
        .execute("SELECT size_category FROM raw_emails WHERE id=?", (r["id"],))
        .fetchone()[0]
        != "micro"
        for r in batch
    )
    cats = {
        sqlite3.connect(db)
        .execute("SELECT size_category FROM raw_emails WHERE id=?", (r["id"],))
        .fetchone()[0]
        for r in batch
    }
    assert "micro" not in cats
    # Prefer scarcest: massive/long/short before medium (medium has 1 golden)
    statuses = dict(
        sqlite3.connect(db).execute(
            "SELECT id, status FROM raw_emails WHERE id BETWEEN 100 AND 202"
        ).fetchall()
    )
    assert statuses[200] == "backtranslated"  # micro untouched
    assert statuses[104] == "locked_v4"  # massive claimed


def test_returns_partial_when_pool_small(tmp_path: Path):
    db = tmp_path / "t2.db"
    _setup_db(db)
    sampler = DiversitySampler(str(db))
    batch = sampler.get_next_batch(100)
    assert len(batch) == 5  # only 5 non-micro ready
    assert all(r["id"] < 200 for r in batch)
