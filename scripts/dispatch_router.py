"""Reflex Q1-Q6 -> executor + dispatch command resolution for /automl v5.10.

Pure function. Inputs: task attributes + env (codex_available + no_codex flag).
Outputs: {executor, command, matched_rows, fallback_reason, rationale}.

Spec: docs/superpowers/specs/2026-05-05-automl-v5.10-design.md M2 + M4.
"""
from __future__ import annotations

from typing import Any

CODEX_DISPATCH_PATH = "~/.claude/skills/codex-dispatch/scripts/codex_dispatch_role.py"


def _match_rows(attrs: dict[str, Any]) -> list[tuple[int, str, str]]:
    """Return matched rows as (row_num, base_executor, label)."""
    matched = []
    if attrs.get("cross_system"):
        matched.append((1, "codex-dispatch:worker", "cross-system"))
    if attrs.get("file_count", 0) >= 3 and attrs.get("architecture_decision"):
        matched.append((2, "codex-dispatch:worker", "multi-file architecture"))
    if attrs.get("exploratory") or not attrs.get("fix_direction_clear", True):
        matched.append((3, "claude:opus", "exploratory"))
    if attrs.get("abstraction"):
        matched.append((4, "codex-dispatch:worker", "abstraction"))
    if attrs.get("naming_or_ui"):
        matched.append((4, "claude:sonnet", "naming/UI"))
    if (
        attrs.get("file_count", 99) == 1
        and attrs.get("spec_complete")
        and not attrs.get("exploratory")
        and attrs.get("fix_direction_clear", True)
    ):
        matched.append((5, "codex-dispatch:worker", "single file + spec complete"))
    if attrs.get("scoped_bug_fix"):
        matched.append((6, "codex-dispatch:worker", "scoped bug fix"))
    if attrs.get("local_refactor"):
        matched.append((7, "codex-dispatch:worker", "local refactor"))
    if attrs.get("unit_test_single_fn"):
        matched.append((8, "codex-dispatch:worker", "unit test single function"))
    if attrs.get("mechanical_plan"):
        matched.append((9, "codex-dispatch:worker", "mechanical plan implementation"))
    return matched


def resolve(attrs: dict[str, Any], codex_available: bool, no_codex: bool) -> dict[str, Any]:
    """Resolve executor and command for a task."""
    matches = _match_rows(attrs)

    if not matches:
        return {
            "executor": "claude:sonnet",
            "command": 'Agent(prompt=TASK_LOOP_PROMPT, model="sonnet")',
            "matched_rows": ["10"],
            "fallback_reason": None,
            "rationale": "no matrix row matched - Row #10 fallback sonnet",
        }

    row_num, base_executor, label = matches[0]
    matched_rows = [str(m[0]) for m in matches]

    fallback_reason = None
    executor = base_executor
    if base_executor == "codex-dispatch:worker":
        if no_codex:
            executor = "claude:sonnet"
            fallback_reason = "no_codex_flag"
        elif not codex_available:
            executor = "claude:sonnet"
            fallback_reason = "codex_unavailable"

    if executor == "codex-dispatch:worker":
        command = f"python3 {CODEX_DISPATCH_PATH} --task <task.md>"
    elif executor == "claude:opus":
        command = 'Agent(prompt=TASK_LOOP_PROMPT, model="opus")'
    elif executor == "claude:sonnet":
        command = 'Agent(prompt=TASK_LOOP_PROMPT, model="sonnet")'
    else:
        raise ValueError(f"unexpected executor: {executor}")

    rationale = f"matched row #{row_num} ({label})"
    if fallback_reason:
        rationale += f" - fallback to {executor} ({fallback_reason})"

    return {
        "executor": executor,
        "command": command,
        "matched_rows": matched_rows,
        "fallback_reason": fallback_reason,
        "rationale": rationale,
    }
