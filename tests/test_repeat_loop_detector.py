import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import repeat_loop_detector as rld


def test_three_same_reasons_triggers():
    log = [{"reason": "A"}, {"reason": "A"}, {"reason": "A"}]
    assert rld.detect_repeat_loop(log) is True


def test_two_same_one_diff_no_trigger():
    log = [{"reason": "A"}, {"reason": "A"}, {"reason": "B"}]
    assert rld.detect_repeat_loop(log) is False


def test_alternating_no_trigger():
    log = [{"reason": "A"}, {"reason": "B"}, {"reason": "A"}]
    assert rld.detect_repeat_loop(log) is False


def test_window_slides_forward():
    """4-entry log with last 3 = A/A/B -> False; new B added -> window B/B/B -> True."""
    log_aab = [{"reason": "A"}, {"reason": "A"}, {"reason": "A"}, {"reason": "B"}]
    assert rld.detect_repeat_loop(log_aab) is False  # last 3 = A/A/B
    log_bbb = log_aab + [{"reason": "B"}, {"reason": "B"}]
    assert rld.detect_repeat_loop(log_bbb) is True  # last 3 = B/B/B


def test_under_3_entries_no_trigger():
    assert rld.detect_repeat_loop([]) is False
    assert rld.detect_repeat_loop([{"reason": "A"}]) is False
    assert rld.detect_repeat_loop([{"reason": "A"}, {"reason": "A"}]) is False


def test_strip_whitespace_match():
    """Trailing whitespace should not cause false negative."""
    log = [{"reason": "A "}, {"reason": "A"}, {"reason": "A\n"}]
    assert rld.detect_repeat_loop(log) is True


def test_custom_n_window():
    """n=2 sliding window."""
    log = [{"reason": "A"}, {"reason": "B"}, {"reason": "B"}]
    assert rld.detect_repeat_loop(log, n=2) is True
