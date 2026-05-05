import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import dispatch_router
import state_io


def _write_state(tmp_path, *, codex_available, no_codex=False):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "5.10",
                "env": {"codex_available": codex_available},
                "flags": {
                    "no_codex": no_codex,
                    "goal": False,
                    "cap": False,
                    "max_ticks_override": None,
                    "max_wall_override": None,
                },
            }
        )
    )
    return state_io.load(state_path)


def test_e2e_cross_system_codex(tmp_path):
    state = _write_state(tmp_path, codex_available=True)

    attrs = {"cross_system": True, "file_count": 2}
    result = dispatch_router.resolve(
        attrs, state["env"]["codex_available"], state["flags"]["no_codex"]
    )

    assert result["executor"] == "codex-dispatch:worker"
    assert "1" in result["matched_rows"]


def test_e2e_cross_system_codex_unavailable_sonnet_fallback(tmp_path):
    state = _write_state(tmp_path, codex_available=False)

    attrs = {"cross_system": True}
    result = dispatch_router.resolve(
        attrs, state["env"]["codex_available"], state["flags"]["no_codex"]
    )

    assert result["executor"] == "claude:sonnet"
    assert result["fallback_reason"] == "codex_unavailable"


def test_e2e_no_codex_flag_sonnet_fallback(tmp_path):
    state = _write_state(tmp_path, codex_available=True, no_codex=True)

    attrs = {"cross_system": True}
    result = dispatch_router.resolve(
        attrs, state["env"]["codex_available"], state["flags"]["no_codex"]
    )

    assert result["executor"] == "claude:sonnet"
    assert result["fallback_reason"] == "no_codex_flag"


def test_e2e_single_file_spec_complete_codex(tmp_path):
    state = _write_state(tmp_path, codex_available=True)

    attrs = {"file_count": 1, "spec_complete": True, "fix_direction_clear": True}
    result = dispatch_router.resolve(
        attrs, state["env"]["codex_available"], state["flags"]["no_codex"]
    )

    assert result["executor"] == "codex-dispatch:worker"
    assert "5" in result["matched_rows"]
