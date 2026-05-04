import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import discord_push


def test_load_webhook_url_reads_config_file(tmp_path):
    """load_webhook_url reads URL from given path, stripped."""
    cfg = tmp_path / "discord_webhook.url"
    cfg.write_text("https://discord.com/api/webhooks/123/abc\n")
    url = discord_push.load_webhook_url(cfg)
    assert url == "https://discord.com/api/webhooks/123/abc"


def test_load_webhook_url_returns_none_if_missing(tmp_path):
    """No file => None (don't crash, just disable push)."""
    cfg = tmp_path / "missing.url"
    assert discord_push.load_webhook_url(cfg) is None


def test_push_skips_when_idempotency_key_already_logged(tmp_path):
    """If idempotency_key is in state.discord_push_log, push is skipped."""
    state = {"discord_push_log": [
        {"idempotency_key": "run-A:complete:2026-05-04T10:00:00", "http_status": 204}
    ]}
    with patch("discord_push.urllib.request.urlopen") as mock_open:
        result = discord_push.push(
            state=state,
            webhook_url="https://example.com/webhook",
            idempotency_key="run-A:complete:2026-05-04T10:00:00",
            content="duplicate push attempt",
        )
    assert result == "skipped_duplicate"
    mock_open.assert_not_called()


def test_push_logs_success(tmp_path):
    """Successful push appends to discord_push_log."""
    state = {"discord_push_log": []}

    class _Resp:
        status = 204
        def read(self): return b""
        def __enter__(self): return self
        def __exit__(self, *_): return False

    with patch("discord_push.urllib.request.urlopen", return_value=_Resp()):
        result = discord_push.push(
            state=state,
            webhook_url="https://example.com/webhook",
            idempotency_key="run-B:complete:2026-05-04T10:00:00",
            content="run B done",
        )
    assert result == "pushed"
    assert len(state["discord_push_log"]) == 1
    assert state["discord_push_log"][0]["http_status"] == 204
