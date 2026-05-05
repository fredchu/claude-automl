"""Sliding-window detector for stuck retry loops in /automl Phase 3.

Spec: docs/superpowers/specs/2026-05-05-automl-v5.10-design.md M6.
"""

from __future__ import annotations

import hashlib


def detect_repeat_loop(retry_log: list[dict], n: int = 3) -> bool:
    """True if last n entries in retry_log share identical reason strings.

    Sliding window: only the most-recent n entries matter. New different reason
    naturally pushes older ones out, so no explicit reset is needed.

    Reason strings are stripped before hashing to tolerate trailing whitespace.

    Args:
        retry_log: list of {"reason": str, ...} dicts; other fields ignored.
        n: window size. Defaults to 3.

    Returns:
        True if all n most-recent entries hash equal; False if shorter than n
        or any pair differs.
    """
    if len(retry_log) < n:
        return False

    recent = [
        hashlib.sha256(entry["reason"].strip().encode()).hexdigest()
        for entry in retry_log[-n:]
    ]
    return len(set(recent)) == 1
