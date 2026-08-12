"""
L4-aware GPU occupancy for Engine V4.

Keeps vLLM saturated (~max useful tok/s) without drowning it in a huge wait queue.
Evidence on inbox-engine (8192 + FP8): ~5–6 running is healthy; 15 emails × 5
parallel genesis produced Waiting≈50 and KV thrash.

Controls:
  - Global LLM in-flight semaphore (default 6)
  - Size-aware genesis/eval fan-out
  - Head+tail trim so prompts fit max_model_len
  - Optional metrics gate: don't admit more work if waiting is already high
"""

from __future__ import annotations

import asyncio
import logging
import os
import urllib.request
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("EngineV4.GpuOccupancy")

# Sweet spot observed on L4 24GB + Qwen2.5-32B-AWQ @ 8192/fp8
DEFAULT_LLM_SLOTS = int(os.getenv("V4_LLM_SLOTS", "6"))
DEFAULT_EMAIL_WORKERS = int(os.getenv("V4_EMAIL_WORKERS", "4"))
MAX_WAIT_BEFORE_ADMIT = int(os.getenv("V4_MAX_VLLM_WAITING", "4"))
VLLM_METRICS_URL = os.getenv("VLLM_METRICS_URL", "http://127.0.0.1:8000/metrics")

# Approx char budget for email body inside prompts (leave room for system/persona/output)
_CHAR_BUDGET = {
    "micro": 6000,
    "short": 8000,
    "medium": 10000,
    "long": 9000,
    "massive": 7000,
}

# Parallel LLM calls per stage (genesis / eval mirror mutation count)
_FANOUT = {
    "micro": 5,
    "short": 5,
    "medium": 4,
    "long": 3,
    "massive": 2,
}

# How many "email seats" a size occupies in the worker admit pool
_SEAT_COST = {
    "micro": 1,
    "short": 1,
    "medium": 1,
    "long": 2,
    "massive": 2,
}

_llm_sem: Optional[asyncio.Semaphore] = None
_seat_lock: Optional[asyncio.Lock] = None
_seats_used: int = 0
_max_seats: int = DEFAULT_EMAIL_WORKERS


def configure(llm_slots: Optional[int] = None, email_seats: Optional[int] = None) -> None:
    global _llm_sem, _max_seats, _seats_used
    slots = llm_slots if llm_slots is not None else DEFAULT_LLM_SLOTS
    _llm_sem = asyncio.Semaphore(slots)
    _max_seats = email_seats if email_seats is not None else DEFAULT_EMAIL_WORKERS
    _seats_used = 0
    logger.warning(
        "GPU occupancy configured: llm_slots=%s email_seats=%s max_wait_admit=%s",
        slots,
        _max_seats,
        MAX_WAIT_BEFORE_ADMIT,
    )


def _ensure() -> None:
    global _llm_sem, _seat_lock
    if _llm_sem is None:
        configure()
    if _seat_lock is None:
        _seat_lock = asyncio.Lock()


def normalize_size(size_category: Optional[str]) -> str:
    if not size_category:
        return "medium"
    return str(size_category).strip().lower()


def seat_cost(size_category: Optional[str]) -> int:
    return _SEAT_COST.get(normalize_size(size_category), 1)


def genesis_fanout(size_category: Optional[str], available_strategies: int) -> int:
    n = _FANOUT.get(normalize_size(size_category), 4)
    return max(1, min(n, available_strategies if available_strategies > 0 else n))


def fit_email_text(text: str, size_category: Optional[str] = None) -> str:
    """Head+tail trim so long/massive bodies fit 8192 context with prompt overhead."""
    if not text:
        return text
    budget = _CHAR_BUDGET.get(normalize_size(size_category), 10000)
    if len(text) <= budget:
        return text
    head = int(budget * 0.65)
    tail = budget - head - 80
    if tail < 200:
        tail = 200
        head = budget - tail - 80
    return (
        text[:head]
        + "\n\n[... truncated for GPU context window; head+tail retained ...]\n\n"
        + text[-tail:]
    )


@asynccontextmanager
async def llm_slot():
    """Acquire one in-flight vLLM request slot (keeps GPU busy, bounds wait queue)."""
    _ensure()
    assert _llm_sem is not None
    await _llm_sem.acquire()
    try:
        yield
    finally:
        _llm_sem.release()


def read_vllm_queue() -> Tuple[Optional[float], Optional[float]]:
    """Return (running, waiting) from vLLM /metrics, or (None, None) on failure."""
    try:
        with urllib.request.urlopen(VLLM_METRICS_URL, timeout=1.5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None, None
    running = waiting = None
    for line in body.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("vllm:num_requests_running{"):
            try:
                running = float(line.rsplit(" ", 1)[-1])
            except ValueError:
                pass
        elif line.startswith("vllm:num_requests_waiting{"):
            try:
                waiting = float(line.rsplit(" ", 1)[-1])
            except ValueError:
                pass
    return running, waiting


async def acquire_email_seat(size_category: Optional[str]) -> int:
    """Block until this email's seat cost fits, and vLLM wait queue is not overloaded."""
    _ensure()
    assert _seat_lock is not None
    cost = seat_cost(size_category)
    while True:
        async with _seat_lock:
            global _seats_used
            running, waiting = await asyncio.to_thread(read_vllm_queue)
            wait_ok = waiting is None or waiting <= MAX_WAIT_BEFORE_ADMIT
            if _seats_used + cost <= _max_seats and wait_ok:
                _seats_used += cost
                logger.info(
                    "admit size=%s cost=%s seats=%s/%s vllm_run=%s vllm_wait=%s",
                    normalize_size(size_category),
                    cost,
                    _seats_used,
                    _max_seats,
                    running,
                    waiting,
                )
                return cost
        await asyncio.sleep(0.35)


async def release_email_seat(cost: int) -> None:
    _ensure()
    assert _seat_lock is not None
    async with _seat_lock:
        global _seats_used
        _seats_used = max(0, _seats_used - cost)


def occupancy_snapshot() -> Dict[str, Any]:
    running, waiting = read_vllm_queue()
    return {
        "llm_slots": DEFAULT_LLM_SLOTS,
        "email_seats_max": _max_seats,
        "email_seats_used": _seats_used,
        "vllm_running": running,
        "vllm_waiting": waiting,
    }
