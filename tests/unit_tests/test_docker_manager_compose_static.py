"""Static checks for manager compose defaults and CI integration-image build flow."""

from pathlib import Path


COMPOSE_PATH = Path("docker/manager/compose.yml")
DOCKERFILE_PATH = Path("docker/manager/Dockerfile")
ENTRYPOINT_PATH = Path("docker/manager/entrypoint.sh")
UNITTEST_WORKFLOW = Path(".github/workflows/unittest.yaml")


def test_manager_compose_defaults_to_latest_image():
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert "image: ${ALPHAGSM_MANAGER_IMAGE:-ghcr.io/sectoralpha/alphagsm:latest}" in text


def test_manager_compose_has_fail_closed_non_root_identity_defaults():
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert 'user: "${ALPHAGSM_HOST_UID:-1000}:${ALPHAGSM_HOST_GID:-1000}"' in text
    assert 'group_add:' in text
    assert '"${ALPHAGSM_DOCKER_GID:-65534}"' in text
    assert "ALPHAGSM_HOST_UID: ${ALPHAGSM_HOST_UID:-1000}" in text
    assert "ALPHAGSM_HOST_GID: ${ALPHAGSM_HOST_GID:-1000}" in text
    assert "ALPHAGSM_DOCKER_GID: ${ALPHAGSM_DOCKER_GID:-65534}" in text
    assert "ALPHAGSM_DOCKER_SOCKET" in text
    assert "Direct Compose" in text


def test_manager_image_and_entrypoint_drop_raw_container_runs_to_mount_owner():
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    entrypoint = ENTRYPOINT_PATH.read_text(encoding="utf-8")

    assert "util-linux" in dockerfile
    assert "exec setpriv" in entrypoint
    assert "--reuid" in entrypoint
    assert "--regid" in entrypoint
    assert "--groups" in entrypoint
    assert 'dirname -- "$config_location"' in entrypoint
    assert "effective UID 0" in entrypoint
    assert "chown -R" not in entrypoint
    assert "sudo" not in entrypoint


def test_pr_workflow_always_builds_integration_image():
    text = UNITTEST_WORKFLOW.read_text(encoding="utf-8")

    assert "Check whether image tag already exists" not in text
    assert "steps.check.outputs.exists" not in text
    assert "Set up Docker Buildx" in text
    assert "Build and push integration test image" in text
