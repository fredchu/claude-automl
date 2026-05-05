# tests/test_state_io.py
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import state_io


def test_load_state_fills_v57_defaults_for_v56_input():
    """Loading a v5.6 state file fills v5.7 defaults: autonomous=false etc."""
    fixture = Path(__file__).parent / "fixtures" / "v5.6_state_phase2.json"
    state = state_io.load(fixture)

    assert state["schema_version"] == "5.6"  # NOT auto-upgraded on read
    assert state["autonomous"] is False
    assert state["lifecycle_state"] == "active"
    assert state["paused"] is False
    assert state["next_wake_at"] is None
    assert state["target_resume_at"] is None
    assert state["last_tick_at"] is None
    assert state["state_version"] == 0
    assert state["quota_state"]["claude"]["consecutive_http_failures"] == 0
    assert state["quota_state"]["codex"]["utilization"] is None
    assert state["quota_history"] == []
    assert state["budget"]["max_total_ticks"] == 50
    assert state["budget"]["max_wall_minutes"] == 480
    assert state["discord_push_log"] == []

    # Original fields preserved
    assert state["phase"] == 2
    assert state["current_task"] == 1
    assert state["task_list"][0]["id"] == 1


def test_cas_write_increments_state_version(tmp_path):
    """Each successful cas_write bumps state_version."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"state_version": 5, "foo": "bar"}))

    state = state_io.load(state_path)
    state["foo"] = "baz"

    new_version = state_io.cas_write(state_path, state, expected_version=5)
    assert new_version == 6

    reloaded = json.loads(state_path.read_text())
    assert reloaded["state_version"] == 6
    assert reloaded["foo"] == "baz"


def test_cas_write_raises_on_version_mismatch(tmp_path):
    """If on-disk version != expected, raise StateConflict (caller can reload+retry)."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"state_version": 7, "foo": "bar"}))

    state = state_io.load(state_path)
    state["foo"] = "baz"

    with pytest.raises(state_io.StateConflict):
        state_io.cas_write(state_path, state, expected_version=5)


def test_cas_write_uses_atomic_rename(tmp_path):
    """Write is atomic: tmpfile + os.replace (no partial writes visible)."""
    import os as os_mod

    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"state_version": 0}))

    captured = {}
    real_replace = os_mod.replace

    def spy_replace(src, dst):
        captured["src"] = src
        captured["dst"] = str(dst)
        real_replace(src, dst)

    with patch("state_io.os.replace", side_effect=spy_replace):
        state_io.cas_write(state_path, {"state_version": 0, "x": 1}, expected_version=0)

    assert captured["dst"] == str(state_path)
    assert ".tmp" in captured["src"] or "tmp" in captured["src"].lower()


def test_cas_write_with_retry_succeeds_after_one_conflict(tmp_path):
    """cas_write_with_retry reloads + reapplies updater on first conflict."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"state_version": 0, "counter": 0}))

    call_count = [0]

    def updater(s: dict) -> None:
        s["counter"] += 1
        # Simulate concurrent writer bumping version externally on first call
        if call_count[0] == 0:
            external = json.loads(state_path.read_text())
            external["state_version"] = 1
            external["counter"] = 999
            state_path.write_text(json.dumps(external))
        call_count[0] += 1

    state_io.cas_write_with_retry(state_path, updater, max_retries=3)

    final = json.loads(state_path.read_text())
    # Counter should be 999 (external write) + 1 (our retry) = 1000
    assert final["counter"] == 1000
    assert final["state_version"] == 2  # 1 (external) + 1 (our successful write)


def test_cas_write_with_retry_raises_after_max_retries(tmp_path):
    """If conflicts exceed max_retries, raise StateConflict."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"state_version": 0}))

    def always_conflict(s: dict) -> None:
        # Each call: bump disk version externally to force perpetual conflict
        external = json.loads(state_path.read_text())
        external["state_version"] += 10
        state_path.write_text(json.dumps(external))

    with pytest.raises(state_io.StateConflict):
        state_io.cas_write_with_retry(state_path, always_conflict, max_retries=3)


def test_v56_run_loaded_then_written_preserves_compat(tmp_path):
    """Full round-trip: load v5.6 fixture, modify (non-autonomous field),
    cas_write, reload — autonomous=false preserved, no v5.7 enabling."""
    src = Path(__file__).parent / "fixtures" / "v5.6_state_phase2.json"
    dst = tmp_path / "state.json"
    dst.write_text(src.read_text())

    state = state_io.load(dst)
    state["current_iter"] = 4  # simulate v5.6 progression
    state_io.cas_write(dst, state, expected_version=0)

    reloaded = state_io.load(dst)
    assert reloaded["current_iter"] == 4
    assert reloaded["autonomous"] is False  # NOT auto-enabled by v5.7 read
    assert reloaded["lifecycle_state"] == "active"
    assert reloaded["state_version"] == 1


def test_load_v5_9_state_default_fills_v5_10_flags(tmp_path):
    """v5.9 state.json missing flags + env → load() default-fills both."""
    p = tmp_path / "state.json"
    p.write_text(json.dumps({
        "schema_version": "5.9",
        "autonomous": True,
        "lifecycle_state": "active",
    }))
    state = state_io.load(p)
    assert state["flags"] == {
        "goal": False, "cap": False,
        "max_ticks_override": None, "max_wall_override": None,
        "no_codex": False,
    }
    assert state["env"] == {"codex_available": None}


def test_load_v5_10_state_with_partial_flags(tmp_path):
    """v5.10 state with partial flags → missing keys default-filled."""
    p = tmp_path / "state.json"
    p.write_text(json.dumps({
        "schema_version": "5.10",
        "flags": {"goal": True},
    }))

    state = state_io.load(p)

    assert state["flags"]["goal"] is True
    assert state["flags"]["cap"] is False
    assert state["flags"]["no_codex"] is False


def test_load_v5_10_state_default_fills_context_state(tmp_path):
    """v5.9 state → context_state default-filled."""
    p = tmp_path / "state.json"
    p.write_text(json.dumps({"schema_version": "5.9"}))
    state = state_io.load(p)
    assert state["context_state"] == {
        "last_check_at": None,
        "used_pct": None,
        "window_size": None,
        "alert_buckets_pushed": [],
        "consecutive_context_failures": 0,
        "window_size_override": None,
    }


def test_load_state_default_fills_context_failures_and_override(tmp_path):
    """v5.10 cleanup: consecutive_context_failures and window_size_override default-filled."""
    p = tmp_path / "state.json"
    p.write_text(json.dumps({"schema_version": "5.9"}))
    state = state_io.load(p)
    assert state["context_state"]["consecutive_context_failures"] == 0
    assert state["context_state"]["window_size_override"] is None
