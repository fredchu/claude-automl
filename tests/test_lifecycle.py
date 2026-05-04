# tests/test_lifecycle.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import lifecycle


def test_valid_transitions():
    """Allowed: active→paused, active→quota_wait, quota_wait→active, quota_wait→paused,
       paused→active, paused→quota_wait, active→complete, active→failed,
       active→budgetLimited, any→cleared, budgetLimited→active (via extend)."""
    valid = [
        ("active", "paused"),
        ("active", "quota_wait"),
        ("active", "complete"),
        ("active", "failed"),
        ("active", "budgetLimited"),
        ("active", "cleared"),
        ("paused", "active"),
        ("paused", "quota_wait"),
        ("paused", "cleared"),
        ("quota_wait", "active"),
        ("quota_wait", "paused"),
        ("quota_wait", "cleared"),
        ("budgetLimited", "active"),  # via /automl resume --extend-budget
        ("budgetLimited", "cleared"),
    ]
    for src, dst in valid:
        assert lifecycle.transition_valid(src, dst), f"should allow {src} -> {dst}"


def test_invalid_transitions():
    """Disallowed: complete/failed/cleared → anything except cleared."""
    invalid = [
        ("complete", "active"),
        ("complete", "paused"),
        ("complete", "quota_wait"),
        ("failed", "active"),
        ("failed", "paused"),
        ("cleared", "active"),
        ("cleared", "paused"),
    ]
    for src, dst in invalid:
        assert not lifecycle.transition_valid(src, dst), f"should reject {src} -> {dst}"


def test_terminal_states():
    """is_terminal returns True for complete/failed/budgetLimited/cleared."""
    assert lifecycle.is_terminal("complete")
    assert lifecycle.is_terminal("failed")
    assert lifecycle.is_terminal("budgetLimited")
    assert lifecycle.is_terminal("cleared")
    assert not lifecycle.is_terminal("active")
    assert not lifecycle.is_terminal("paused")
    assert not lifecycle.is_terminal("quota_wait")


def test_should_short_circuit_at_tick_start():
    """paused / terminal states short-circuit at tick start (no work done)."""
    for state in ["paused", "complete", "failed", "budgetLimited", "cleared"]:
        assert lifecycle.should_short_circuit(state), f"{state} should short-circuit"
    for state in ["active", "quota_wait"]:
        assert not lifecycle.should_short_circuit(state), f"{state} should NOT short-circuit"
