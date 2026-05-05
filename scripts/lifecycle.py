# scripts/lifecycle.py
"""Lifecycle state machine for /automl v5.7 autonomous mode.

Pure functions — no I/O. Validated transitions per spec §6 + §8.1.
"""
from __future__ import annotations


VALID_STATES = frozenset({
    "active", "paused", "quota_wait",
    "context_critical",
    "complete", "failed", "budgetLimited", "cleared",
})

# context_critical is NOT terminal - user can /clear + resume
TERMINAL_STATES = frozenset({"complete", "failed", "budgetLimited", "cleared"})

# (src, dst) → allowed
ALLOWED_TRANSITIONS = frozenset({
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
    # Recovery via --extend-budget
    ("budgetLimited", "active"),
    ("budgetLimited", "cleared"),
})

ALLOWED_TRANSITIONS = ALLOWED_TRANSITIONS | frozenset({
    ("active", "context_critical"),
    ("context_critical", "active"),
    ("context_critical", "paused"),
    ("context_critical", "cleared"),
})


def transition_valid(src: str, dst: str) -> bool:
    """True if transitioning src→dst is allowed."""
    if src == dst:
        return True  # idempotent
    return (src, dst) in ALLOWED_TRANSITIONS


def is_terminal(state: str) -> bool:
    """True if state is terminal (no autonomous wake should be scheduled)."""
    return state in TERMINAL_STATES


def should_short_circuit(state: str) -> bool:
    """True if tick should short-circuit at top.

    context_critical must not dispatch subagents because that would inflate
    context further. User must manually /clear + /automl resume.
    """
    return state in {"paused", "context_critical"} or is_terminal(state)
