"""Anthropic OAuth quota helper for /automl autonomous mode.

Pure HTTP -- does not depend on LLM. Safe to call from quota-exhausted state.
See spec docs/superpowers/specs/2026-05-04-automl-autonomous-mode-design.md §5.2.1.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


KEYCHAIN_SERVICE = "Claude Code-credentials"
OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_BETA_HEADER = "oauth-2025-04-20"
RELEVANT_BUCKETS = ("five_hour", "seven_day", "seven_day_sonnet", "seven_day_opus")
CACHE_TTL_SECONDS = 30
DEFAULT_CACHE_PATH = Path.home() / ".automl" / "quota_cache.json"


def read_token() -> str:
    """Read the Anthropic OAuth access token from macOS Keychain."""
    raw = subprocess.check_output(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"]
    )
    payload = json.loads(raw.decode().strip())
    return payload["claudeAiOauth"]["accessToken"]


def fetch_quota(token: str, timeout: float = 10.0) -> dict:
    """Hit Anthropic OAuth usage endpoint, return parsed JSON."""
    req = urllib.request.Request(
        OAUTH_USAGE_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": OAUTH_BETA_HEADER,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def check_buckets(quota: dict, threshold: float) -> tuple[str, float, str] | None:
    """Return (name, utilization, resets_at) of first bucket >= threshold; None if all under."""
    for name in RELEVANT_BUCKETS:
        bucket = quota.get(name)
        if bucket is None:
            continue
        util = bucket.get("utilization")
        if util is None:
            continue
        if util >= threshold:
            return (name, util, bucket["resets_at"])
    return None


def query(cache_path: Path = DEFAULT_CACHE_PATH) -> dict:
    """Query quota, using on-disk cache if last fetch was within CACHE_TTL_SECONDS."""
    now = time.time()
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            if now - cached["fetched_at"] < CACHE_TTL_SECONDS:
                return cached["quota"]
        except (json.JSONDecodeError, KeyError):
            pass  # corrupt cache -> refetch

    token = read_token()
    quota = fetch_quota(token)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"fetched_at": now, "quota": quota}))
    return quota


def query_with_retry(state: dict, cache_path: Path = DEFAULT_CACHE_PATH):
    """Wrap query() with fail-closed counter tracking on state.

    Returns:
        - dict (the quota response) on success; resets counter to 0
        - "http_failed" on HTTP/network failure; increments counter
    """
    claude = state.setdefault("quota_state", {}).setdefault("claude", {})
    try:
        quota = query(cache_path=cache_path)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError, subprocess.CalledProcessError):
        claude["consecutive_http_failures"] = claude.get("consecutive_http_failures", 0) + 1
        return "http_failed"
    claude["consecutive_http_failures"] = 0
    return quota


def _main():
    """CLI: print current quota as JSON. Used by automl SKILL.md prompts."""
    import sys
    try:
        quota = query()
        print(json.dumps(quota, indent=2))
        sys.exit(0)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()
