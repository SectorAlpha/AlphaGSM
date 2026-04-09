"""Static contract tests for Docker backend integration coverage."""

from pathlib import Path


BACKEND_DOCKER_TEST = Path("tests/backend_integration_tests/test_backend_docker.py")
BACKEND_DOCKER_MANAGER_TEST = Path("tests/backend_integration_tests/test_backend_docker_manager.py")
WORKFLOW_PATH = Path(".github/workflows/unittest.yaml")


def test_backend_docker_test_parametrizes_active_family_cases():
    text = BACKEND_DOCKER_TEST.read_text()

    assert '@pytest.mark.parametrize("case", family_matrix.active_cases(),' in text


def test_backend_docker_test_covers_alpha_gsm_lifecycle_contract():
    text = BACKEND_DOCKER_TEST.read_text()
    required_snippets = (
        '"create"',
        '"setup"',
        '"start"',
        '"status"',
        '"query"',
        '"info"',
        '"info", "--json"',
        '"stop"',
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_backend_docker_manager_test_covers_alpha_gsm_lifecycle_contract():
    text = BACKEND_DOCKER_MANAGER_TEST.read_text()
    required_snippets = (
        '"create"',
        '"setup"',
        '"start"',
        '"status"',
        '"query"',
        '"info"',
        '"info",',
        '"--json"',
        '"stop"',
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_backend_ci_workflow_explicitly_runs_docker_backend_tests():
    text = WORKFLOW_PATH.read_text()

    assert "tests/backend_integration_tests/test_backend_docker.py" in text
    assert "tests/backend_integration_tests/test_backend_docker_manager.py" in text
    assert 'ALPHAGSM_RUN_BACKEND_INTEGRATION: "1"' in text


def test_summarize_tests_includes_backend_integration_results():
    text = WORKFLOW_PATH.read_text()

    assert "needs: [smoke-test, integration-test, backend-integration-test]" in text
    assert "backend-integration-results-" in text
    assert 'glob.glob("artifacts/backend-integration-results-*/*.xml")' in text
