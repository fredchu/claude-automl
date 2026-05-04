import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import quota_check


def test_read_token_from_keychain_uses_security_cli():
    """Helper must call macOS `security` CLI to fetch the OAuth token."""
    fake_keychain_payload = json.dumps({
        "claudeAiOauth": {"accessToken": "sk-ant-oat01-FAKE"}
    })
    with patch("quota_check.subprocess.check_output") as mock_run:
        mock_run.return_value = fake_keychain_payload.encode()
        token = quota_check.read_token()
    mock_run.assert_called_once_with(
        ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"]
    )
    assert token == "sk-ant-oat01-FAKE"


def test_fetch_quota_calls_oauth_endpoint_with_required_headers():
    """fetch_quota must hit the OAuth usage endpoint with the beta header."""
    fake_response_body = json.dumps({
        "five_hour":  {"utilization": 53.0, "resets_at": "2026-05-04T04:40:00+00:00"},
        "seven_day":  {"utilization": 17.0, "resets_at": "2026-05-08T08:00:00+00:00"},
        "seven_day_sonnet": {"utilization": 1.0, "resets_at": "2026-05-08T08:00:00+00:00"},
        "seven_day_opus": None,
        "extra_usage": {"is_enabled": True, "monthly_limit": 2000, "used_credits": 0.0},
    })

    class _Resp:
        status = 200
        def read(self): return fake_response_body.encode()
        def __enter__(self): return self
        def __exit__(self, *_): return False

    with patch("quota_check.urllib.request.urlopen") as mock_open:
        mock_open.return_value = _Resp()
        body = quota_check.fetch_quota("FAKE_TOKEN")
    req = mock_open.call_args.args[0]
    assert req.full_url == "https://api.anthropic.com/api/oauth/usage"
    assert req.get_header("Authorization") == "Bearer FAKE_TOKEN"
    assert req.get_header("Anthropic-beta") == "oauth-2025-04-20"
    assert body["five_hour"]["utilization"] == 53.0


def test_check_buckets_returns_first_violating_bucket():
    """check_buckets returns the first bucket >= threshold, or None if all under."""
    # All under threshold
    assert quota_check.check_buckets(
        {"five_hour": {"utilization": 50.0, "resets_at": "X"},
         "seven_day": {"utilization": 60.0, "resets_at": "Y"}},
        threshold=75.0,
    ) is None

    # five_hour exceeds
    triggered = quota_check.check_buckets(
        {"five_hour": {"utilization": 80.0, "resets_at": "X"},
         "seven_day": {"utilization": 60.0, "resets_at": "Y"}},
        threshold=75.0,
    )
    assert triggered == ("five_hour", 80.0, "X")

    # null bucket is ignored
    assert quota_check.check_buckets(
        {"five_hour": None,
         "seven_day": {"utilization": 50.0, "resets_at": "Y"}},
        threshold=75.0,
    ) is None


def test_query_uses_cache_within_30_seconds(tmp_path):
    """query() returns cached response if last_check < 30s ago."""
    cache_path = tmp_path / "quota_cache.json"
    fake_response = {"five_hour": {"utilization": 50.0, "resets_at": "X"}}

    with patch("quota_check.read_token", return_value="T"), \
         patch("quota_check.fetch_quota", return_value=fake_response) as mock_fetch:
        result1 = quota_check.query(cache_path=cache_path)
        result2 = quota_check.query(cache_path=cache_path)

    assert mock_fetch.call_count == 1  # second call hit cache
    assert result1 == result2


def test_query_with_retry_increments_failure_counter_on_http_error(tmp_path):
    """When fetch_quota raises, query_with_retry increments consecutive_http_failures."""
    cache_path = tmp_path / "quota_cache.json"
    state = {"quota_state": {"claude": {"consecutive_http_failures": 0}}}

    import urllib.error
    with patch("quota_check.read_token", return_value="T"), \
         patch("quota_check.fetch_quota", side_effect=urllib.error.URLError("boom")):
        result = quota_check.query_with_retry(state, cache_path=cache_path)

    assert result == "http_failed"
    assert state["quota_state"]["claude"]["consecutive_http_failures"] == 1


def test_query_with_retry_resets_counter_on_success(tmp_path):
    """Successful fetch resets consecutive_http_failures to 0."""
    cache_path = tmp_path / "quota_cache.json"
    state = {"quota_state": {"claude": {"consecutive_http_failures": 2}}}

    with patch("quota_check.read_token", return_value="T"), \
         patch("quota_check.fetch_quota", return_value={"five_hour": {"utilization": 50.0, "resets_at": "X"}}):
        result = quota_check.query_with_retry(state, cache_path=cache_path)

    assert result["five_hour"]["utilization"] == 50.0
    assert state["quota_state"]["claude"]["consecutive_http_failures"] == 0
