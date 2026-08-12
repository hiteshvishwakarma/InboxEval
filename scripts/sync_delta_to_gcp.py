"""
sync_delta_to_gcp.py
──────────────────────────────────────────────────────────────────────────────
Safely pushes enriched raw_emails rows from the local Mac pipeline.db to the
GCP VM's pipeline.db — WITHOUT touching the golden_dataset table.

HOW IT WORKS:
  1. Reads local Mac DB for fully-complete rows (prompt+persona+dpbc) not in sync_log.
  2. UPDATE enrichment columns on GCP with BEGIN IMMEDIATE + AND status='pending'.
  3. SSH pipe failure => transaction rollback; local sync_log only updated after SYNC_OK.
  4. Optionally filter by diversity_batch --batch-id.
  5. Chroma rsync under chroma_write_lock after SQL success.

USAGE:
  python3 scripts/sync_delta_to_gcp.py --dry-run
  python3 scripts/sync_delta_to_gcp.py --verify --batch-id <id>
"""

from __future__ import annotations

import argparse
import logging
import os
import shlex
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PIPELINE = os.path.join(_ROOT, "scripts", "data_pipeline")
sys.path.insert(0, _ROOT)
sys.path.insert(0, _PIPELINE)

from chroma_lock import chroma_write_lock
from diversity_batch import ensure_diversity_batch_table, get_batch_ids

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("SyncDeltaToGCP")

LOCAL_DB = os.path.abspath(os.path.join(_ROOT, "data/pipeline.db"))
GCP_SSH_ALIAS = "inbox-engine"
GCP_DB_PATH = "/home/hitesh/InboxEval/data/pipeline.db"
SYNC_COLS = ["prompt", "context", "target_persona", "dpbc_targets", "status"]


def ssh_python(
    script: str,
    *,
    input_text: str | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """
    Run a Python snippet on GCP via SSH.

    Must use shlex.quote — nesting python3 -c '...' with inner single quotes
    strips path quotes and breaks bash (seen as: sqlite3.connect(/home/...)).
    """
    remote = f"python3 -c {shlex.quote(script)}"
    return subprocess.run(
        ["ssh", GCP_SSH_ALIAS, remote],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def ensure_sync_log(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            raw_email_id  INTEGER PRIMARY KEY,
            synced_at     TEXT NOT NULL
        )
    """)
    conn.commit()


def get_unsynced_rows(conn: sqlite3.Connection, batch_id: str | None = None) -> list:
    """Fully complete non-micro rows not yet in sync_log; optional batch filter."""
    conn.row_factory = sqlite3.Row
    ensure_diversity_batch_table(conn)

    if batch_id:
        ids = get_batch_ids(conn, batch_id)
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        cursor = conn.execute(
            f"""
            SELECT id, prompt, context, target_persona, dpbc_targets, status
            FROM   raw_emails
            WHERE  status          = 'backtranslated'
              AND  prompt          IS NOT NULL
              AND  target_persona  IS NOT NULL
              AND  dpbc_targets    IS NOT NULL
              AND  size_category   != 'micro'
              AND  id IN ({placeholders})
              AND  id NOT IN (SELECT raw_email_id FROM sync_log)
            """,
            ids,
        )
    else:
        cursor = conn.execute("""
            SELECT id, prompt, context, target_persona, dpbc_targets, status
            FROM   raw_emails
            WHERE  status          = 'backtranslated'
              AND  prompt          IS NOT NULL
              AND  target_persona  IS NOT NULL
              AND  dpbc_targets    IS NOT NULL
              AND  size_category   != 'micro'
              AND  id NOT IN (SELECT raw_email_id FROM sync_log)
        """)
    return [dict(r) for r in cursor.fetchall()]


def build_gcp_sql(rows: list) -> str:
    """Atomic UPDATE script; never references golden_dataset."""

    def esc(v):
        if v is None:
            return "NULL"
        return "'" + str(v).replace("'", "''") + "'"

    lines = [
        "PRAGMA busy_timeout = 30000;",
        "BEGIN IMMEDIATE;",
    ]
    for row in rows:
        sets = ", ".join(f"{col} = {esc(row.get(col))}" for col in SYNC_COLS)
        lines.append(
            f"UPDATE raw_emails SET {sets} "
            f"WHERE id = {row['id']} AND status = 'pending';"
        )
    lines.append("COMMIT;")
    return "\n".join(lines)


def gcp_golden_count() -> int | None:
    """Snapshot golden_dataset COUNT(*) on GCP before sync."""
    gcp_python = (
        "import sqlite3\n"
        f"conn = sqlite3.connect({GCP_DB_PATH!r}, timeout=30)\n"
        "print(conn.execute('SELECT COUNT(*) FROM golden_dataset').fetchone()[0])\n"
        "conn.close()\n"
    )
    try:
        result = ssh_python(gcp_python, timeout=30)
        if result.returncode != 0:
            logger.error("Failed to read golden_dataset count: %s", result.stderr)
            return None
        return int(result.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError) as e:
        logger.error("golden_dataset count error: %s", e)
        return None


def run_on_gcp(sql: str) -> bool:
    gcp_python = (
        "import sqlite3, sys\n"
        "sql = sys.stdin.read()\n"
        f"conn = sqlite3.connect({GCP_DB_PATH!r}, timeout=30)\n"
        "conn.executescript(sql)\n"
        "conn.close()\n"
        "print('SYNC_OK')\n"
    )
    try:
        result = ssh_python(gcp_python, input_text=sql, timeout=120)
        if result.returncode != 0 or "SYNC_OK" not in result.stdout:
            logger.error("GCP error:\n%s\n%s", result.stderr, result.stdout)
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error(
            "SSH timeout — GCP did not respond in 120s. "
            "Transaction rolled back. Safe to retry."
        )
        return False


def fetch_applied_ids_on_gcp(ids: list) -> list[int]:
    """Return IDs that now look enriched on GCP (status backtranslated + dpbc set)."""
    if not ids:
        return []
    id_list = ",".join(str(i) for i in ids)
    gcp_python = (
        "import sqlite3\n"
        f"conn = sqlite3.connect({GCP_DB_PATH!r}, timeout=30)\n"
        "c = conn.cursor()\n"
        f"c.execute('SELECT id FROM raw_emails WHERE id IN ({id_list}) "
        f"AND status = \"backtranslated\" AND dpbc_targets IS NOT NULL')\n"
        "print(','.join(str(r[0]) for r in c.fetchall()))\n"
        "conn.close()\n"
    )
    try:
        result = ssh_python(gcp_python, timeout=60)
        if result.returncode != 0:
            logger.error("Failed to verify applied IDs: %s", result.stderr)
            return []
        line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        if not line:
            return []
        return [int(x) for x in line.split(",") if x.strip().isdigit()]
    except (subprocess.TimeoutExpired, ValueError) as e:
        logger.error("applied-id verify error: %s", e)
        return []


def mark_synced(conn: sqlite3.Connection, ids: list) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT OR REPLACE INTO sync_log(raw_email_id, synced_at) VALUES (?, ?)",
        [(id_, now) for id_ in ids],
    )
    conn.commit()


def verify_on_gcp(ids: list, golden_before: int | None) -> None:
    id_list = ",".join(str(i) for i in ids[:10])
    gcp_python = (
        "import sqlite3\n"
        f"conn = sqlite3.connect({GCP_DB_PATH!r}, timeout=10)\n"
        "c = conn.cursor()\n"
        f"c.execute('SELECT id, size_category, status, "
        f"prompt IS NOT NULL, target_persona IS NOT NULL, dpbc_targets IS NOT NULL "
        f"FROM raw_emails WHERE id IN ({id_list})')\n"
        "print('id | cat | status | has_prompt | has_persona | has_dpbc')\n"
        "for r in c.fetchall(): print(r)\n"
        "c.execute('SELECT COUNT(*) FROM golden_dataset')\n"
        "print('golden_dataset rows:', c.fetchone()[0])\n"
        "conn.close()\n"
    )
    result = ssh_python(gcp_python, timeout=30)
    logger.info("GCP spot-check (first 10 IDs):\n%s", result.stdout)
    if golden_before is not None and result.stdout:
        for line in result.stdout.splitlines():
            if line.startswith("golden_dataset rows:"):
                try:
                    after = int(line.split(":", 1)[1].strip())
                    if after != golden_before:
                        logger.error(
                            "golden_dataset COUNT changed (%s -> %s) — investigate!",
                            golden_before,
                            after,
                        )
                    else:
                        logger.info(
                            "golden_dataset COUNT unchanged (%s) — OK", golden_before
                        )
                except ValueError:
                    pass


def sync_chroma(lock_timeout: float = 1800) -> None:
    local_chroma = os.path.abspath(os.path.join(_ROOT, "data/chroma_db/"))
    if not os.path.exists(local_chroma):
        logger.warning("ChromaDB directory not found locally — skipping chroma sync.")
        return
    logger.info("Syncing ChromaDB vectors to GCP under chroma_write_lock...")
    with chroma_write_lock(timeout_sec=lock_timeout, holder="sync_delta_chroma"):
        result = subprocess.run(
            [
                "rsync",
                "-avz",
                "--checksum",
                local_chroma + "/",
                f"{GCP_SSH_ALIAS}:/home/hitesh/InboxEval/data/chroma_db/",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    if result.returncode == 0:
        logger.info("ChromaDB sync complete.")
    else:
        logger.error("ChromaDB rsync failed:\n%s", result.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync enriched Mac rows to GCP pipeline.db"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--skip-chroma", action="store_true")
    parser.add_argument("--batch-id", default=None, help="Only sync this diversity_batch")
    parser.add_argument("--lock-timeout", type=float, default=1800)
    args = parser.parse_args()

    if not os.path.exists(LOCAL_DB):
        logger.error("Local DB not found: %s", LOCAL_DB)
        sys.exit(1)

    conn = sqlite3.connect(LOCAL_DB, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    ensure_sync_log(conn)
    rows = get_unsynced_rows(conn, args.batch_id)

    if not rows:
        logger.info(
            "Nothing to sync — no fully-complete rows "
            "(prompt+persona+dpbc all non-null) found."
        )
        conn.close()
        return

    logger.info(
        "Found %s FULLY COMPLETE rows to sync (Step1+Step2a both done):", len(rows)
    )
    logger.info(
        "  Sample IDs    : %s%s",
        [r["id"] for r in rows[:5]],
        "..." if len(rows) > 5 else "",
    )
    logger.info("  Columns pushed: %s", SYNC_COLS)
    logger.info("  Safety guard  : BEGIN IMMEDIATE + AND status='pending'")
    logger.info("  golden_dataset: NEVER TOUCHED")
    if args.batch_id:
        logger.info("  batch_id      : %s", args.batch_id)

    if args.dry_run:
        sql = build_gcp_sql(rows)
        print("\n── DRY RUN: first 3 UPDATE statements ──────────────────────────")
        updates = [l for l in sql.splitlines() if l.startswith("UPDATE")]
        for l in updates[:3]:
            print(l[:140] + ("..." if len(l) > 140 else ""))
        print(
            f"\n[{len(rows)} total UPDATEs, each guarded by AND status='pending' — no SSH made]"
        )
        conn.close()
        return

    golden_before = gcp_golden_count()
    if golden_before is not None:
        logger.info("GCP golden_dataset COUNT before sync: %s", golden_before)

    logger.info("Pushing SQL delta to GCP via SSH (%s)...", GCP_SSH_ALIAS)
    sql = build_gcp_sql(rows)
    success = run_on_gcp(sql)

    if success:
        ids = [r["id"] for r in rows]
        applied = fetch_applied_ids_on_gcp(ids)
        skipped = sorted(set(ids) - set(applied))
        if applied:
            mark_synced(conn, applied)
            logger.info(
                "SQL sync SUCCESS: %s/%s IDs confirmed enriched on GCP. Watermark updated.",
                len(applied),
                len(ids),
            )
        else:
            logger.warning(
                "SQL ran but 0 IDs confirmed as backtranslated+dpbc on GCP. "
                "Not watermarking — safe to retry."
            )
        if skipped:
            logger.warning(
                "Skipped watermark for %s IDs (not pending on GCP or not applied): %s%s",
                len(skipped),
                skipped[:10],
                "..." if len(skipped) > 10 else "",
            )
        if args.verify and applied:
            verify_on_gcp(applied, golden_before)
        elif golden_before is not None:
            golden_after = gcp_golden_count()
            if golden_after is not None and golden_after != golden_before:
                logger.error(
                    "golden_dataset COUNT changed (%s -> %s)",
                    golden_before,
                    golden_after,
                )
            elif golden_after == golden_before:
                logger.info("golden_dataset COUNT unchanged (%s)", golden_before)
    else:
        logger.error(
            "SQL sync FAILED — nothing written to GCP (transaction rolled back). "
            "Safe to retry."
        )
        conn.close()
        return

    if not args.skip_chroma:
        sync_chroma(lock_timeout=args.lock_timeout)
    else:
        logger.info("ChromaDB sync skipped (--skip-chroma).")

    conn.close()


if __name__ == "__main__":
    main()
