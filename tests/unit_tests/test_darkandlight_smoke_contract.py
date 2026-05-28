"""Static contract checks for the darkandlightserver smoke runner."""

from pathlib import Path


SMOKE_SCRIPT = Path("tests/smoke_tests/run_darkandlightserver.sh")


def test_darkandlight_smoke_runner_checks_udp_query_and_info_on_game_port():
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'wait_for_info_protocol "$SERVER_NAME" udp "$START_TIMEOUT_SECONDS"' in text
    assert 'run_alphagsm_capture() {' in text
    assert 'query_output="$(run_alphagsm_capture "$SERVER_NAME" query)"' in text
    assert 'Server port is open (UDP ping on port $PORT' in text
    assert 'info_json_output="$(run_alphagsm_capture "$SERVER_NAME" info --json)"' in text
    assert 'EXPECTED_PORT="$PORT" INFO_JSON_PAYLOAD="$info_json_output"' in text
    assert 'wait_for_generic_udp_closed "$PORT" "$STOP_TIMEOUT_SECONDS"' in text
