"""Static contract checks for the Mumble integration test image selection."""

from pathlib import Path


INTEGRATION_TEST = Path("tests/integration_tests/test_mumbleserver.py")


def test_mumble_integration_prefers_the_ci_simple_tcp_runtime_image():
    text = INTEGRATION_TEST.read_text(encoding="utf-8")

    assert "resolve_runtime_image" in text
    assert '"ALPHAGSM_BACKEND_DOCKER_IMAGE_SIMPLE_TCP"' in text
    assert '"alphagsm-simple-tcp-runtime:test"' in text
