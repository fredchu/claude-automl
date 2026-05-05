"""Discord webhook push helper for /automl autonomous mode.

Loads webhook URL from ~/.config/automl/discord_webhook.url (gitignored).
Idempotency-keyed POST + push log appender. Spec §5.3.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_WEBHOOK_PATH = Path.home() / ".config" / "automl" / "discord_webhook.url"


def load_webhook_url(path: Path = DEFAULT_WEBHOOK_PATH) -> str | None:
    """Load webhook URL from secret config; None if missing or empty."""
    if not path.exists():
        return None
    url = path.read_text().strip()
    return url or None


def push(*, state: dict, webhook_url: str, idempotency_key: str, content: str) -> str:
    """Push a message to Discord; idempotency-keyed.

    Returns:
        - "pushed" on success
        - "skipped_duplicate" if idempotency_key already in log
        - "skipped_no_webhook" if webhook_url is None
        - "failed:<reason>" on HTTP failure (logged but not raised; spec §5.3 fail handling)
    """
    if not webhook_url:
        return "skipped_no_webhook"

    log = state.setdefault("discord_push_log", [])
    if any(entry.get("idempotency_key") == idempotency_key for entry in log):
        return "skipped_duplicate"

    payload = json.dumps({"content": content}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.append({
                "timestamp": timestamp,
                "idempotency_key": idempotency_key,
                "http_status": resp.status,
            })
        return "pushed"
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        log.append({
            "timestamp": timestamp,
            "idempotency_key": idempotency_key,
            "http_status": "failed",
            "error": str(exc)[:200],
        })
        return f"failed:{type(exc).__name__}"


def format_context_critical(run_id: str, used_pct: float, used_tokens: int, window_size: int) -> str:
    """Critical: context >= 80%, tick paused, user must /clear + resume."""
    return (
        f"⚠️ Run {run_id} → context_critical. "
        f"Context {used_pct:.1f}% ({used_tokens:,} / {window_size:,}). "
        f"已停止派 subagent。請手動 `/automl pause` → `/clear` → `/automl resume` 重啟。"
    )


def format_context_hint(run_id: str, bucket: int, used_pct: float) -> str:
    """Hint: context crossed 60/65/70/75% bucket; clear at next 5h gate."""
    return (
        f"💡 Run {run_id} context {used_pct:.1f}% (crossed {bucket}% bucket). "
        f"建議下個 5h gate 進入時手動 `/clear` + resume，避免後續觸發 80% critical。"
    )


def format_repeat_loop(run_id: str, reason: str) -> str:
    """Repeat-loop escape valve triggered."""
    return (
        f"🛑 Run {run_id} → failed (repeat-loop detected). "
        f"Phase 2 反覆修同問題（最近 3 次 retry 原因相同）：「{reason[:120]}」"
        f"\n需人工介入。"
    )
