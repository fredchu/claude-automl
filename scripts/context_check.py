"""Read transcript JSONL, compute context %, infer window size.

Spec: docs/superpowers/specs/2026-05-05-automl-v5.10-design.md section M1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Model name -> context window lookup. 1M variants are detected via observed
# inference when the transcript model name does not encode the variant.
MODEL_WINDOW_LOOKUP = {
    "claude-opus-4-7": 1_000_000,
    "claude-opus-4-6": 200_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5": 200_000,
}
DEFAULT_WINDOW = 1_000_000


def _used_tokens(usage: dict[str, Any]) -> int:
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )


def check(
    transcript_path: str | Path, window_size_override: int | None = None
) -> dict[str, Any]:
    """Read last assistant message usage from transcript and compute context %.

    Window size resolution priority:
    1. ``window_size_override`` when provided.
    2. Observed inference: any historical used tokens > 200k means 1M window.
    3. Lookup by model name.
    4. Conservative default fallback of 1M for unknown models.

    Raises:
        ValueError: If no assistant message with usage exists in the transcript.
    """
    path = Path(transcript_path)
    last_usage: dict[str, Any] | None = None
    last_model = "unknown"
    max_observed = 0

    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "assistant":
                continue

            message = obj.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue

            observed = _used_tokens(usage)
            max_observed = max(max_observed, observed)
            last_usage = usage
            last_model = message.get("model", "unknown")

    if last_usage is None:
        raise ValueError(f"no assistant message with usage in {path}")

    last_used = _used_tokens(last_usage)

    if window_size_override is not None:
        window_size = window_size_override
        window_source = "override"
    elif max_observed > 200_000:
        window_size = 1_000_000
        window_source = "observed"
    else:
        window_size = MODEL_WINDOW_LOOKUP.get(last_model, DEFAULT_WINDOW)
        window_source = "lookup"

    return {
        "used_tokens": last_used,
        "used_percentage": round(last_used / window_size * 100, 2),
        "window_size": window_size,
        "model": last_model,
        "window_source": window_source,
    }
