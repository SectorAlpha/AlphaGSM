"""Static contract checks for the darkandlightserver smoke runner."""

from pathlib import Path


SMOKE_SCRIPT = Path("tests/smoke_tests/run_darkandlightserver.sh")


def test_darkandlight_smoke_runner_checks_udp_query_and_info_on_game_port():
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'LOCAL_DOCKER_IMAGE="alphagsm-wine-proton-runtime:local"' in text
    assert 'backend = docker' in text
    assert 'run_alphagsm "$SERVER_NAME" set image "$DOCKER_IMAGE"' in text
    assert 'wait_for_info_protocol "$SERVER_NAME" "udp" "$START_TIMEOUT_SECONDS"' in text
    assert 'query_output="$(run_alphagsm_capture "$SERVER_NAME" query)"' in text
    assert 'Server port is open (UDP ping on port $PORT' in text
    assert 'run_alphagsm "$SERVER_NAME" info' in text
    assert 'run_alphagsm "$SERVER_NAME" info --json' in text
    assert 'wait_for_generic_udp_closed "127.0.0.1" "$PORT" "$STOP_TIMEOUT_SECONDS"' in text
