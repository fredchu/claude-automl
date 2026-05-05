import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import dispatch_router as dr


def _attrs(file_count=1, cross_system=False, architecture=False,
           exploratory=False, abstraction=False, naming_or_ui=False,
           spec_complete=True, fix_direction_clear=True):
    return {
        "file_count": file_count,
        "cross_system": cross_system,
        "architecture_decision": architecture,
        "exploratory": exploratory,
        "abstraction": abstraction,
        "naming_or_ui": naming_or_ui,
        "spec_complete": spec_complete,
        "fix_direction_clear": fix_direction_clear,
    }


def test_row1_cross_system_codex():
    """Row #1: cross-system -> codex:worker."""
    r = dr.resolve(_attrs(cross_system=True), codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"
    assert "1" in r["matched_rows"]


def test_row2_multi_file_arch_codex():
    """Row #2: multi-file architecture -> codex:worker."""
    r = dr.resolve(_attrs(file_count=4, architecture=True), codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"


def test_row3_exploratory_opus():
    """Row #3: exploratory -> claude:opus."""
    r = dr.resolve(_attrs(exploratory=True, fix_direction_clear=False), codex_available=True, no_codex=False)
    assert r["executor"] == "claude:opus"


def test_row4a_abstraction_codex():
    """Row #4a: abstraction -> codex:worker."""
    r = dr.resolve(_attrs(abstraction=True), codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"


def test_row4b_naming_ui_sonnet():
    """Row #4b: naming/UI -> claude:sonnet."""
    r = dr.resolve(_attrs(naming_or_ui=True), codex_available=True, no_codex=False)
    assert r["executor"] == "claude:sonnet"


def test_row5_single_file_spec_complete_codex():
    """Row #5: single file + spec complete -> codex:worker."""
    r = dr.resolve(_attrs(file_count=1, spec_complete=True), codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"


def test_row6_scoped_bug_fix_codex():
    """Row #6: scoped bug fix -> codex:worker."""
    attrs = _attrs(file_count=2)
    attrs["scoped_bug_fix"] = True
    r = dr.resolve(attrs, codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"
    assert "6" in r["matched_rows"]


def test_row7_local_refactor_codex():
    """Row #7: local refactor -> codex:worker."""
    attrs = _attrs(file_count=2)
    attrs["local_refactor"] = True
    r = dr.resolve(attrs, codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"
    assert "7" in r["matched_rows"]


def test_row8_unit_test_codex():
    """Row #8: unit test for single function -> codex:worker."""
    attrs = _attrs(file_count=2)
    attrs["unit_test_single_fn"] = True
    r = dr.resolve(attrs, codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"
    assert "8" in r["matched_rows"]


def test_row9_mechanical_plan_codex():
    """Row #9: mechanical plan -> codex:worker."""
    attrs = _attrs(file_count=2)
    attrs["mechanical_plan"] = True
    r = dr.resolve(attrs, codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"
    assert "9" in r["matched_rows"]


def test_rows6_to_9_fallback_when_codex_unavailable():
    """Rows #6-#9 are codex rows, so codex unavailable falls back to sonnet."""
    for attr_name in ("scoped_bug_fix", "local_refactor", "unit_test_single_fn", "mechanical_plan"):
        attrs = _attrs(file_count=2)
        attrs[attr_name] = True
        r = dr.resolve(attrs, codex_available=False, no_codex=False)
        assert r["executor"] == "claude:sonnet"
        assert r["fallback_reason"] == "codex_unavailable"


def test_row10_fallback_sonnet():
    """Row #10: nothing matches -> claude:sonnet."""
    r = dr.resolve(_attrs(spec_complete=False, fix_direction_clear=False), codex_available=True, no_codex=False)
    # exploratory=False but fix_direction_clear=False -> still hits Row #3 (exploratory clause covers either)
    # We need a true no-match case
    # ... actually any of {exploratory or not fix_direction_clear} hits #3.
    # For Row #10 we need: not cross_system, not (>=3 files + arch), not exploratory, fix_direction_clear=True,
    # not abstraction, not naming/ui, not (file_count==1 + spec_complete)
    r = dr.resolve(_attrs(file_count=2, spec_complete=False, fix_direction_clear=True), codex_available=True, no_codex=False)
    assert r["executor"] == "claude:sonnet"
    assert "10" in r["matched_rows"]


def test_codex_unavailable_fallback_to_sonnet_except_opus():
    """codex_available=False: codex rows fallback to sonnet, opus row stays opus."""
    r = dr.resolve(_attrs(cross_system=True), codex_available=False, no_codex=False)
    assert r["executor"] == "claude:sonnet"
    assert r["fallback_reason"] == "codex_unavailable"

    r2 = dr.resolve(_attrs(exploratory=True, fix_direction_clear=False), codex_available=False, no_codex=False)
    assert r2["executor"] == "claude:opus"  # Row #3 opus preserved (no fallback)


def test_no_codex_flag_fallback():
    """--no-codex flag forces sonnet for codex rows, preserves opus."""
    r = dr.resolve(_attrs(cross_system=True), codex_available=True, no_codex=True)
    assert r["executor"] == "claude:sonnet"
    assert r["fallback_reason"] == "no_codex_flag"

    r2 = dr.resolve(_attrs(exploratory=True, fix_direction_clear=False), codex_available=True, no_codex=True)
    assert r2["executor"] == "claude:opus"


def test_command_codex_worker():
    r = dr.resolve(_attrs(cross_system=True), codex_available=True, no_codex=False)
    assert r["executor"] == "codex-dispatch:worker"
    assert "codex_dispatch_role.py" in r["command"]


def test_command_claude_agents():
    r = dr.resolve(_attrs(exploratory=True, fix_direction_clear=False), codex_available=True, no_codex=False)
    assert r["command"] == 'Agent(prompt=TASK_LOOP_PROMPT, model="opus")'

    r2 = dr.resolve(_attrs(naming_or_ui=True), codex_available=True, no_codex=False)
    assert r2["command"] == 'Agent(prompt=TASK_LOOP_PROMPT, model="sonnet")'
