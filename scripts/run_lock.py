"""Single-run autonomous lock for /automl v5.7.

Tier 2 spec §5.1: only one active autonomous run per repo at a time.
This helper scans .automl/*/state.json to enforce that invariant.
"""
from __future__ import annotations

import json
from pathlib import Path


ACTIVE_LIKE_STATES = frozenset({"active", "quota_wait"})


class LockInvariantViolation(Exception):
    """Raised when more than one active autonomous run is found."""


def find_active_autonomous(automl_dir: Path) -> str | None:
    """Return run_id of the active autonomous run, or None if none.

    Raises LockInvariantViolation if 2+ active runs are found (caller must
    pause/clear extras before proceeding).
    """
    if not automl_dir.exists():
        return None

    actives = []
    for run_dir in automl_dir.iterdir():
        state_file = run_dir / "state.json"
        if not state_file.exists():
            continue
        try:
            state = json.loads(state_file.read_text())
        except json.JSONDecodeError:
            continue
        if not state.get("autonomous"):
            continue
        if state.get("lifecycle_state") in ACTIVE_LIKE_STATES:
            actives.append(state.get("run_id", run_dir.name))

    if len(actives) > 1:
        raise LockInvariantViolation(f"Multiple active autonomous runs: {actives}")
    return actives[0] if actives else None
