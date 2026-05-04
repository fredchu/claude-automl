# scripts/state_io.py
"""State.json read/write helpers for /automl v5.7 autonomous mode.

Provides:
  - load(): read with v5.6->v5.7 default-fill (additive backward compat)
  - cas_write(): atomic rename + state_version CAS for concurrent-write safety

Spec §6 + §8.1 E8.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


V57_DEFAULTS: dict[str, Any] = {
    "autonomous": False,
    "lifecycle_state": "active",
    "paused": False,
    "next_wake_at": None,
    "target_resume_at": None,
    "last_tick_at": None,
    "state_version": 0,
    "quota_state": {
        "claude": {
            "last_check_at": None,
            "utilization": None,
            "resets_at": None,
            "triggered_bucket": None,
            "throttle_until": None,
            "consecutive_http_failures": 0,
        },
        "codex": {
            "last_check_at": None,
            "utilization": None,
            "resets_at": None,
        },
    },
    "quota_history": [],
    "budget": {
        "max_total_ticks": 50,
        "max_wall_minutes": 480,
        "ticks_used": 0,
        "started_at": None,
    },
    "discord_push_log": [],
}


def _deep_default_fill(state: dict, defaults: dict) -> None:
    """In-place: for any key missing in state, copy default. Recurse on dicts."""
    for key, default_val in defaults.items():
        if key not in state:
            state[key] = json.loads(json.dumps(default_val))  # deep copy
        elif isinstance(default_val, dict) and isinstance(state[key], dict):
            _deep_default_fill(state[key], default_val)


def load(path: Path) -> dict:
    """Load state.json with v5.7 default-fill for missing fields."""
    with open(path) as f:
        state = json.load(f)
    _deep_default_fill(state, V57_DEFAULTS)
    return state


class StateConflict(Exception):
    """Raised when expected state_version does not match on-disk version."""


def cas_write(path: Path, state: dict, *, expected_version: int) -> int:
    """Atomically write state.json with optimistic concurrency control.

    Reads current state_version from disk, raises StateConflict if it has
    advanced past expected_version. On success, increments state_version
    and writes via tmpfile + os.replace.

    Returns: new state_version on success.
    """
    # Re-read disk version for comparison
    if path.exists():
        with open(path) as f:
            on_disk = json.load(f)
        on_disk_version = on_disk.get("state_version", 0)
        if on_disk_version != expected_version:
            raise StateConflict(
                f"state_version mismatch: expected {expected_version}, found {on_disk_version}"
            )
    elif expected_version != 0:
        raise StateConflict(
            f"expected_version {expected_version} but file does not exist"
        )

    state["state_version"] = expected_version + 1

    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp.json",
        prefix=path.name + ".",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if Path(tmp_path).exists():
            os.unlink(tmp_path)
        raise

    return state["state_version"]


def cas_write_with_retry(path: Path, updater, max_retries: int = 3) -> int:
    """Reload state, apply updater, cas_write. Retry on StateConflict up to max_retries.

    `updater(state: dict) -> None` mutates state in place. State is reloaded
    fresh on each retry so updater always sees latest disk state.

    Returns: new state_version after successful write.
    Raises: StateConflict after max_retries attempts.
    """
    for attempt in range(max_retries):
        try:
            state = load(path)
            current_version = state.get("state_version", 0)
            updater(state)
            return cas_write(path, state, expected_version=current_version)
        except StateConflict:
            if attempt == max_retries - 1:
                raise
            continue
    raise StateConflict(f"Exceeded max_retries={max_retries}")
