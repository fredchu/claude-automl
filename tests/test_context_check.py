import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import context_check as cc


def _make_jsonl(tmp_path, entries):
    p = tmp_path / "session.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries))
    return p


def test_compute_pct_basic(tmp_path):
    """input + cache_creation + cache_read divided by window."""
    p = _make_jsonl(
        tmp_path,
        [
            {
                "type": "assistant",
                "message": {
                    "model": "claude-opus-4-7",
                    "usage": {
                        "input_tokens": 50000,
                        "cache_read_input_tokens": 20000,
                        "cache_creation_input_tokens": 10000,
                        "output_tokens": 100,
                    },
                },
            }
        ],
    )
    r = cc.check(p)
    assert r["used_tokens"] == 80000
    assert r["window_size"] == 1_000_000
    assert abs(r["used_percentage"] - 8.0) < 0.1


def test_window_observed_inference_above_200k(tmp_path):
    """If observed used > 200k, infer 1M (overrides 200k lookup)."""
    p = _make_jsonl(
        tmp_path,
        [
            {
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-4-6",
                    "usage": {
                        "input_tokens": 250000,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 100,
                    },
                },
            }
        ],
    )
    r = cc.check(p)
    assert r["window_size"] == 1_000_000
    assert r["window_source"] == "observed"


def test_window_override(tmp_path):
    """Explicit override takes precedence."""
    p = _make_jsonl(
        tmp_path,
        [
            {
                "type": "assistant",
                "message": {
                    "model": "claude-opus-4-7",
                    "usage": {
                        "input_tokens": 100000,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 100,
                    },
                },
            }
        ],
    )
    r = cc.check(p, window_size_override=500_000)
    assert r["window_size"] == 500_000
    assert r["window_source"] == "override"


def test_unknown_model_fallback_1m(tmp_path):
    """Unknown model -> fallback 1M (conservative - avoids false alarm)."""
    p = _make_jsonl(
        tmp_path,
        [
            {
                "type": "assistant",
                "message": {
                    "model": "claude-future-9000",
                    "usage": {
                        "input_tokens": 100000,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 100,
                    },
                },
            }
        ],
    )
    r = cc.check(p)
    assert r["window_size"] == 1_000_000
    assert r["window_source"] == "lookup"


def test_empty_transcript_raises(tmp_path):
    """Empty file -> raises (caller decides fail-open behavior)."""
    p = tmp_path / "empty.jsonl"
    p.write_text("")
    import pytest

    with pytest.raises(ValueError):
        cc.check(p)


def test_skips_non_assistant_entries(tmp_path):
    """Pulls usage from last assistant message, skipping user/tool entries."""
    p = _make_jsonl(
        tmp_path,
        [
            {
                "type": "assistant",
                "message": {
                    "model": "claude-opus-4-7",
                    "usage": {
                        "input_tokens": 10000,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 100,
                    },
                },
            },
            {"type": "user", "message": {"content": "hello"}},
            {
                "type": "assistant",
                "message": {
                    "model": "claude-opus-4-7",
                    "usage": {
                        "input_tokens": 50000,
                        "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "output_tokens": 200,
                    },
                },
            },
        ],
    )
    r = cc.check(p)
    assert r["used_tokens"] == 50000
