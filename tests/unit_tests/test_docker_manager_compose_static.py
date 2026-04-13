"""Static checks for manager compose defaults and CI integration-image build flow."""

from pathlib import Path


COMPOSE_PATH = Path("docker/manager/compose.yml")
UNITTEST_WORKFLOW = Path(".github/workflows/unittest.yaml")


def test_manager_compose_defaults_to_latest_with_pull_policy():
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert "image: ${ALPHAGSM_MANAGER_IMAGE:-ghcr.io/sectoralpha/alphagsm:latest}" in text
    assert "pull_policy: missing" in text


def test_pr_workflow_always_builds_integration_image():
    text = UNITTEST_WORKFLOW.read_text(encoding="utf-8")

    assert "Check whether image tag already exists" not in text
    assert "steps.check.outputs.exists" not in text
    assert "Set up Docker Buildx" in text
    assert "Build and push integration test image" in text
