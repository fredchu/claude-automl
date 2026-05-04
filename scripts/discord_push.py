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
