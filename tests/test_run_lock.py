import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import run_lock


def _write_state(automl_dir: Path, run_id: str, autonomous: bool, lifecycle_state: str):
    run_dir = automl_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "schema_version": "5.7",
        "run_id": run_id,
        "autonomous": autonomous,
        "lifecycle_state": lifecycle_state,
    }))


def test_no_active_returns_none(tmp_path):
    automl = tmp_path / ".automl"
    automl.mkdir()
    assert run_lock.find_active_autonomous(automl) is None


def test_one_active_autonomous_returns_run_id(tmp_path):
    automl = tmp_path / ".automl"
    _write_state(automl, "run-A", autonomous=True, lifecycle_state="active")
    _write_state(automl, "run-B", autonomous=False, lifecycle_state="active")
    assert run_lock.find_active_autonomous(automl) == "run-A"


def test_quota_wait_counts_as_active(tmp_path):
    automl = tmp_path / ".automl"
    _write_state(automl, "run-Z", autonomous=True, lifecycle_state="quota_wait")
    assert run_lock.find_active_autonomous(automl) == "run-Z"


def test_terminal_states_dont_count(tmp_path):
    automl = tmp_path / ".automl"
    for run, state in [("r1", "complete"), ("r2", "failed"),
                       ("r3", "budgetLimited"), ("r4", "cleared"), ("r5", "paused")]:
        _write_state(automl, run, autonomous=True, lifecycle_state=state)
    assert run_lock.find_active_autonomous(automl) is None


def test_two_active_raises(tmp_path):
    """Two active autonomous runs is an invariant violation — caller must clean up."""
    automl = tmp_path / ".automl"
    _write_state(automl, "run-A", autonomous=True, lifecycle_state="active")
    _write_state(automl, "run-B", autonomous=True, lifecycle_state="active")
    with pytest.raises(run_lock.LockInvariantViolation):
        run_lock.find_active_autonomous(automl)
