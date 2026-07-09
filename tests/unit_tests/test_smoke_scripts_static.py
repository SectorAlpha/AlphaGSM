"""Static contract tests for smoke runners that should follow declared runtimes."""

from pathlib import Path


LIFE_IS_FEUDAL_SMOKE = Path("tests/smoke_tests/run_lifeisfeudalserver.sh")
SCUM_SMOKE = Path("tests/smoke_tests/run_scumserver.sh")


def test_life_is_feudal_smoke_uses_docker_runtime_backend():
    text = LIFE_IS_FEUDAL_SMOKE.read_text(encoding="utf-8")

    assert "[runtime]" in text
    assert "backend = docker" in text
    assert "image_wine_proton = $IMAGE" in text


def test_life_is_feudal_smoke_resolves_wine_proton_image_instead_of_screen():
    text = LIFE_IS_FEUDAL_SMOKE.read_text(encoding="utf-8")

    assert 'ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON' in text
    assert 'run_alphagsm "$SERVER_NAME" set image "$IMAGE"' in text
    assert 'require_cmd screen' not in text


def test_scum_smoke_uses_shared_work_root_and_start_retry_contract():
    text = SCUM_SMOKE.read_text(encoding="utf-8")

    assert 'WORK_ROOT="$(resolve_work_root)"' in text
    assert 'WORK_DIR="$(mktemp -d -p "$WORK_ROOT" scumserver-smoke.XXXXXX)"' in text
    assert 'run_start_with_port_retry "$SERVER_NAME"' in text
    assert 'run_alphagsm "$SERVER_NAME" start' not in text
