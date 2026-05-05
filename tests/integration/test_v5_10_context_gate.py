import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import context_check as cc
import discord_push
import lifecycle
import state_io


def _transcript(tmp_path, used_tokens):
    """Create a transcript with the given used_tokens in the last assistant turn."""
    p = tmp_path / "session.jsonl"
    p.write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "claude-opus-4-7",
                    "usage": {
                        "input_tokens": used_tokens,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 100,
                    },
                },
            }
        )
        + "\n"
    )
    return p


def _state(tmp_path, context_state=None):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "5.10",
                "run_id": "20260505-100000-abc",
                "lifecycle_state": "active",
                "context_state": context_state or {},
            }
        )
    )
    return state_io.load(state_path)


def _hint_bucket(used_percentage):
    if 60 <= used_percentage < 80:
        return int(used_percentage // 5) * 5
    return None


def _push_hint_once(state, *, bucket, used_percentage):
    pushed = state["context_state"]["alert_buckets_pushed"]
    if bucket in pushed:
        return "skipped_bucket_duplicate"

    result = discord_push.push(
        state=state,
        webhook_url="https://example.com/webhook",
        idempotency_key=f"{state['run_id']}:context_hint:{bucket}",
        content=discord_push.format_context_hint(
            state["run_id"],
            bucket,
            used_percentage,
        ),
    )
    pushed.append(bucket)
    return result


def test_below_60_no_alert_state_change(tmp_path):
    """Context under 60 percent stays outside alert buckets."""
    state = _state(tmp_path)
    p = _transcript(tmp_path, 500_000)

    r = cc.check(p)
    bucket = _hint_bucket(r["used_percentage"])

    assert r["used_percentage"] == 50.0
    assert bucket is None
    assert state["lifecycle_state"] == "active"
    assert state["context_state"]["alert_buckets_pushed"] == []


def test_60_to_80_hint_bucket(tmp_path):
    """Context in [60, 80) maps to a 5 percent hint bucket."""
    p = _transcript(tmp_path, 700_000)

    r = cc.check(p)
    bucket = _hint_bucket(r["used_percentage"])
    msg = discord_push.format_context_hint(
        "20260505-100000-abc",
        bucket,
        r["used_percentage"],
    )

    assert r["used_percentage"] == 70.0
    assert bucket == 70
    assert "70" in msg
    assert "context" in msg.lower()


def test_above_80_enters_context_critical_lifecycle(tmp_path):
    """Context at or above 80 percent may enter context_critical and stop work."""
    p = _transcript(tmp_path, 850_000)

    r = cc.check(p)
    msg = discord_push.format_context_critical(
        "20260505-100000-abc",
        r["used_percentage"],
        r["used_tokens"],
        r["window_size"],
    )

    assert r["used_percentage"] == 85.0
    assert lifecycle.transition_valid("active", "context_critical")
    assert lifecycle.should_short_circuit("context_critical")
    assert not lifecycle.is_terminal("context_critical")
    assert "/clear" in msg


def test_alert_buckets_do_not_double_push(tmp_path):
    """A bucket already recorded in context_state skips a second hint push."""
    state = _state(tmp_path, {"alert_buckets_pushed": [60, 65]})
    p = _transcript(tmp_path, 675_000)

    r = cc.check(p)
    bucket = _hint_bucket(r["used_percentage"])

    with patch("discord_push.urllib.request.urlopen") as mock_open:
        result = _push_hint_once(state, bucket=bucket, used_percentage=r["used_percentage"])

    assert bucket == 65
    assert result == "skipped_bucket_duplicate"
    assert state["context_state"]["alert_buckets_pushed"] == [60, 65]
    mock_open.assert_not_called()


def test_critical_idempotency_key_shape(tmp_path):
    """Critical idempotency key includes run_id, state, and first_entry_ts."""
    state = _state(tmp_path)
    first_entry_ts = "2026-05-05T13:00:00"
    key = f"{state['run_id']}:context_critical:{first_entry_ts}"

    parts = key.split(":")

    assert parts[0] == "20260505-100000-abc"
    assert parts[1] == "context_critical"
    assert ":".join(parts[2:]) == first_entry_ts
