"""Static contract checks for the darkandlightserver smoke runner."""

from pathlib import Path


SMOKE_SCRIPT = Path("tests/smoke_tests/run_darkandlightserver.sh")


def test_darkandlight_smoke_runner_checks_udp_query_and_info_on_game_port():
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'wait_for_udp_or_fail_fast() {' in text
    assert 'wait_for_udp_or_fail_fast "$SERVER_NAME" "$START_TIMEOUT_SECONDS"' in text
    assert 'run_alphagsm_capture() {' in text
    assert 'Dark and Light screen session died before UDP readiness' in text
    assert 'Server isn\'t running as no screen session' in text
    assert 'screen log tail ($screen_log_path):' in text
    assert 'DNL log tail ($LOG_PATH):' in text
    assert 'query_output="$(run_alphagsm_capture "$SERVER_NAME" query)"' in text
    assert 'Server port is open (UDP ping on port $PORT' in text
    assert 'wait_for_generic_udp_closed "$PORT" "$STOP_TIMEOUT_SECONDS"' in text
