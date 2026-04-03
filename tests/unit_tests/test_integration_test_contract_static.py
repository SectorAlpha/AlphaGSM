"""Static contract tests for integration test files."""

from pathlib import Path


INTEGRATION_TEST_DIR = Path("tests/integration_tests")
SPECIAL_CASES = {"test_archive_backed_installs.py"}


def _integration_test_files():
    return sorted(
        path
        for path in INTEGRATION_TEST_DIR.glob("test_*.py")
        if path.name not in SPECIAL_CASES
    )


def test_integration_tests_do_not_allow_tcp_fallback_output():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if 'or "Server port is open" in query_result.stdout' in text:
            offenders.append(f"{path}: query fallback")
        if 'or "Server port is open" in info_result.stdout' in text:
            offenders.append(f"{path}: info fallback")

    assert offenders == []


def test_integration_tests_require_exact_protocol_assertions():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if '_info_data["protocol"] in (' in text:
            offenders.append(str(path))

    assert offenders == []


def test_integration_tests_do_not_soft_pass_query_info_commands():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if "if query_result.returncode == 0:" in text:
            offenders.append(f"{path}: query")
        if "if info_result.returncode == 0:" in text:
            offenders.append(f"{path}: info")
        if "if info_json_result.returncode == 0:" in text:
            offenders.append(f"{path}: info-json")

    assert offenders == []


def test_a2s_integration_tests_do_not_accept_hibernation_as_success():
    offenders = []
    for path in _integration_test_files():
        text = path.read_text()
        if "wait_for_a2s_ready" in text and "Server is hibernating" in text:
            offenders.append(str(path))

    assert offenders == []
