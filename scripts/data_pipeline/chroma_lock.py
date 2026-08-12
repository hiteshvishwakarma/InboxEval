"""
Exclusive flock around data/chroma_db for Step 02b writes, Step 02a reads, and sync rsync.

Wait/retry until the lock is free (default 30 minutes). Does not drop caller work —
callers resume after acquiring the lock. On timeout, raise TimeoutError; claimed DB
rows remain resumable (dpbc_targets IS NULL / Chroma upsert-by-id).
"""

from __future__ import annotations

import fcntl
import logging
import os
import time
from contextlib import contextmanager
from typing import Iterator, Optional

logger = logging.getLogger("ChromaLock")

DEFAULT_CHROMA_DIR = os.path.abspath("data/chroma_db")
LOCK_FILENAME = ".chroma_access.lock"
DEFAULT_TIMEOUT_SEC = 1800
POLL_INTERVAL_SEC = 2.0


def lock_path(chroma_dir: Optional[str] = None) -> str:
    """Return absolute path to the Chroma access lock file."""
    base = os.path.abspath(chroma_dir or DEFAULT_CHROMA_DIR)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, LOCK_FILENAME)


@contextmanager
def chroma_write_lock(
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    chroma_dir: Optional[str] = None,
    poll_interval_sec: float = POLL_INTERVAL_SEC,
    holder: str = "chroma",
) -> Iterator[None]:
    """
    Acquire an exclusive flock on data/chroma_db/.chroma_access.lock.

    Blocks with wait/retry until acquired or timeout_sec elapses.
    Lock is process-bound; crash releases it (no stale manual unlock).
    """
    path = lock_path(chroma_dir)
    deadline = time.monotonic() + timeout_sec
    fd = open(path, "a+", encoding="utf-8")
    acquired = False
    logged_wait = False
    try:
        while True:
            try:
                fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                fd.seek(0)
                fd.truncate()
                fd.write(f"holder={holder}\npid={os.getpid()}\n")
                fd.flush()
                logger.info("Chroma lock acquired by %s (pid=%s)", holder, os.getpid())
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"Chroma lock busy for {timeout_sec:.0f}s "
                        f"(holder waiting: {holder}). Batch work is still resumable — retry later."
                    )
                if not logged_wait:
                    logger.info(
                        "Chroma busy — %s waiting (retry every %.1fs, timeout %.0fs)...",
                        holder,
                        poll_interval_sec,
                        timeout_sec,
                    )
                    logged_wait = True
                time.sleep(min(poll_interval_sec, remaining))
        yield
    finally:
        if acquired:
            try:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
                logger.info("Chroma lock released by %s (pid=%s)", holder, os.getpid())
            except OSError:
                pass
        fd.close()
