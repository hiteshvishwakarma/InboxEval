"""Smoke tests for L4 GPU occupancy helpers."""

from src.engine_v4.golden_dataset_generator_v4.gpu_occupancy import (
    fit_email_text,
    genesis_fanout,
    seat_cost,
)


def test_genesis_fanout_by_size():
    assert genesis_fanout("short", 5) == 5
    assert genesis_fanout("medium", 5) == 4
    assert genesis_fanout("long", 5) == 3
    assert genesis_fanout("massive", 5) == 2
    assert genesis_fanout("massive", 1) == 1


def test_seat_cost():
    assert seat_cost("short") == 1
    assert seat_cost("long") == 2
    assert seat_cost("massive") == 2


def test_fit_email_preserves_short():
    text = "hello world"
    assert fit_email_text(text, "short") == text


def test_fit_email_trims_massive():
    text = "A" * 50000
    out = fit_email_text(text, "massive")
    assert len(out) < len(text)
    assert "truncated" in out
    assert out.startswith("A")
    assert out.endswith("A")
