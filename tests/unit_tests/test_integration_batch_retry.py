"""Tests for the integration batch retry helper."""

from pathlib import Path
import xml.etree.ElementTree as ET

from tests.helpers import load_module_from_repo


SCRIPT_PATH = Path("scripts/run_integration_batch_with_retry.py")
WORKFLOW_PATH = Path(".github/workflows/unittest.yaml")


def load_retry_module():
    assert SCRIPT_PATH.exists(), f"missing retry helper: {SCRIPT_PATH}"
    return load_module_from_repo("integration_batch_retry", str(SCRIPT_PATH))


def write_report(path, cases):
    suite = ET.Element("testsuite")
    for classname, name, outcome in cases:
        testcase = ET.SubElement(suite, "testcase", classname=classname, name=name)
        if outcome == "failure":
            ET.SubElement(testcase, "failure", message="boom")
        elif outcome == "error":
            ET.SubElement(testcase, "error", message="crash")
        elif outcome == "skipped":
            ET.SubElement(testcase, "skipped", message="skip")
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def _testcase_map(path):
    root = ET.parse(path).getroot()
    cases = {}
    for testcase in root.iter("testcase"):
        key = (testcase.attrib["classname"], testcase.attrib["name"])
        cases[key] = testcase
    return cases


def test_pytest_nodeid_from_testcase_supports_module_and_class_cases():
    retry = load_retry_module()

    module_case = ET.Element(
        "testcase",
        classname="tests.integration_tests.test_alpha",
        name="test_server_lifecycle",
    )
    class_case = ET.Element(
        "testcase",
        classname="tests.integration_tests.test_beta.TestServer",
        name="test_query[param]",
    )

    assert retry.pytest_nodeid_from_testcase(module_case) == (
        "tests/integration_tests/test_alpha.py::test_server_lifecycle"
    )
    assert retry.pytest_nodeid_from_testcase(class_case) == (
        "tests/integration_tests/test_beta.py::TestServer::test_query[param]"
    )


def test_failing_test_nodeids_returns_only_failed_cases(tmp_path):
    retry = load_retry_module()
    report = tmp_path / "results.xml"
    write_report(
        report,
        [
            ("tests.integration_tests.test_alpha", "test_ok", "passed"),
            ("tests.integration_tests.test_alpha", "test_fail", "failure"),
            ("tests.integration_tests.test_beta.TestServer", "test_boom", "error"),
            ("tests.integration_tests.test_gamma", "test_skip", "skipped"),
        ],
    )

    assert retry.failing_test_nodeids(report) == [
        "tests/integration_tests/test_alpha.py::test_fail",
        "tests/integration_tests/test_beta.py::TestServer::test_boom",
    ]


def test_merge_junit_reports_replaces_retried_failures(tmp_path):
    retry = load_retry_module()
    initial = tmp_path / "initial.xml"
    rerun = tmp_path / "rerun.xml"
    merged = tmp_path / "results.xml"

    write_report(
        initial,
        [
            ("tests.integration_tests.test_alpha", "test_ok", "passed"),
            ("tests.integration_tests.test_alpha", "test_flaky", "failure"),
            ("tests.integration_tests.test_beta", "test_skip", "skipped"),
        ],
    )
    write_report(
        rerun,
        [
            ("tests.integration_tests.test_alpha", "test_flaky", "passed"),
        ],
    )

    retry.merge_junit_reports(initial, rerun, merged)

    cases = _testcase_map(merged)
    assert set(cases) == {
        ("tests.integration_tests.test_alpha", "test_ok"),
        ("tests.integration_tests.test_alpha", "test_flaky"),
        ("tests.integration_tests.test_beta", "test_skip"),
    }
    assert cases[("tests.integration_tests.test_alpha", "test_flaky")].find("failure") is None
    assert cases[("tests.integration_tests.test_beta", "test_skip")].find("skipped") is not None


def test_workflow_uses_integration_retry_helper():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "scripts/run_integration_batch_with_retry.py" in text
    assert "--results-file results.xml" in text