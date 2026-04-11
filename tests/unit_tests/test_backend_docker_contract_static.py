"""Static contract tests for Docker backend integration coverage."""

from pathlib import Path

from tests.helpers import load_module_from_repo


BACKEND_DOCKER_TEST = Path("tests/backend_integration_tests/test_backend_docker.py")
BACKEND_DOCKER_MANAGER_TEST = Path("tests/backend_integration_tests/test_backend_docker_manager.py")
BACKEND_DOCKER_WRAPPER_TEST = Path("tests/backend_integration_tests/test_alphagsm_docker_wrapper.py")
WORKFLOW_PATH = Path(".github/workflows/unittest.yaml")

family_matrix = load_module_from_repo(
    "backend_docker_family_matrix_static_contract",
    "tests/backend_integration_tests/docker_family_matrix.py",
)


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


def test_backend_docker_wrapper_test_covers_status_and_info_lifecycle_contract():
    text = BACKEND_DOCKER_WRAPPER_TEST.read_text()
    required_snippets = (
        '"create"',
        '"setup"',
        '"start"',
        '"status"',
        '"info"',
        '"info",',
        '"--json"',
        '"stop"',
        '"down"',
        '"Host connection details:"',
    )

    missing = [snippet for snippet in required_snippets if snippet not in text]

    assert missing == []


def test_docker_family_matrix_declares_three_cases_for_each_runtime_family():
    cases = family_matrix.all_cases()
    families = sorted({case.runtime_family for case in cases})

    assert families == [
        "java",
        "quake-linux",
        "service-console",
        "simple-tcp",
        "steamcmd-linux",
        "wine-proton",
    ]

    for family in families:
        family_cases = [case for case in cases if case.runtime_family == family]
        assert len(family_cases) == 3, (family, [case.slug for case in family_cases])


def test_backend_ci_workflow_explicitly_runs_docker_backend_tests():
    text = WORKFLOW_PATH.read_text()

    assert "tests/backend_integration_tests/test_backend_docker.py" in text
    assert "tests/backend_integration_tests/test_backend_docker_manager.py" in text
    assert "tests/backend_integration_tests/test_alphagsm_docker_wrapper.py" in text
    assert 'ALPHAGSM_RUN_BACKEND_INTEGRATION: "1"' in text


def test_summarize_tests_includes_backend_integration_results():
    text = WORKFLOW_PATH.read_text()

    assert "needs: [smoke-test, integration-test, backend-integration-test]" in text
    assert "backend-integration-results-" in text
    assert 'glob.glob("artifacts/backend-integration-results-*/*.xml")' in text
