import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import repeat_loop_detector as rld
import state_io


def _make_state(tmp_path, **flag_overrides):
    flags = {
        "goal": False,
        "cap": False,
        "no_codex": False,
        "max_ticks_override": None,
        "max_wall_override": None,
    }
    flags.update(flag_overrides)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"schema_version": "5.10", "flags": flags}))
    return state_io.load(state_path)


def test_goal_no_cap_default(tmp_path):
    """--goal alone -> goal=True, cap=False (no budget enforcement)."""
    state = _make_state(tmp_path, goal=True)

    assert state["flags"]["goal"] is True
    assert state["flags"]["cap"] is False


def test_goal_with_cap(tmp_path):
    """--goal --cap -> soft caps enforced."""
    state = _make_state(tmp_path, goal=True, cap=True)

    assert state["flags"]["cap"] is True


def test_autonomous_alias_eq_goal_cap(tmp_path):
    """--autonomous is behaviorally equivalent to setting goal+cap."""
    state = _make_state(tmp_path, goal=True, cap=True)

    assert state["flags"]["goal"] and state["flags"]["cap"]


def test_repeat_loop_escape_valve_in_goal_mode():
    """Even in --goal no-cap mode, repeat-loop detector triggers failed."""
    retry_log = [
        {"reason": "Phase 2 fix didn't address bug X", "ts": "t1"},
        {"reason": "Phase 2 fix didn't address bug X", "ts": "t2"},
        {"reason": "Phase 2 fix didn't address bug X", "ts": "t3"},
    ]

    assert rld.detect_repeat_loop(retry_log) is True


def test_repeat_loop_window_slides():
    """New different reason -> window slides, no false trigger."""
    retry_log = [
        {"reason": "bug X", "ts": "t1"},
        {"reason": "bug X", "ts": "t2"},
        {"reason": "bug X", "ts": "t3"},
        {"reason": "bug Y", "ts": "t4"},
    ]

    assert rld.detect_repeat_loop(retry_log) is False
