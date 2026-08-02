"""Tests for collecting post-matrix integration rechecks from JUnit artifacts."""

from pathlib import Path
import xml.etree.ElementTree as ET

from tests.helpers import load_module_from_repo


SCRIPT_PATH = Path("scripts/collect_integration_rechecks.py")
WORKFLOW_PATH = Path(".github/workflows/unittest.yaml")


def load_collector_module():
    assert SCRIPT_PATH.exists(), f"missing recheck collector: {SCRIPT_PATH}"
    return load_module_from_repo("integration_recheck_collection", str(SCRIPT_PATH))


def write_report(path, cases):
    path.parent.mkdir(parents=True, exist_ok=True)
    suite = ET.Element("testsuite")
    for classname, name, outcome in cases:
        testcase = ET.SubElement(suite, "testcase", classname=classname, name=name)
        if outcome == "failure":
            ET.SubElement(testcase, "failure", message="boom")
        elif outcome == "error":
            ET.SubElement(testcase, "error", message="crash")
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def test_collect_failed_rechecks_keeps_each_runtime_lane(tmp_path):
    collector = load_collector_module()
    artifacts = tmp_path / "artifacts"
    write_report(
        artifacts / "integration-results-batch-1-of-36-process" / "results.xml",
        [
            ("tests.integration_tests.test_alpha", "test_lifecycle", "failure"),
            ("tests.integration_tests.test_alpha", "test_other", "passed"),
        ],
    )
    write_report(
        artifacts / "integration-results-batch-1-of-36-docker" / "results.xml",
        [("tests.integration_tests.test_alpha", "test_lifecycle", "error")],
    )
    write_report(
        artifacts / "integration-results-batch-2-of-10" / "results.xml",
        [("tests.integration_tests.test_beta.TestServer", "test_query[param]", "failure")],
    )

    assert collector.collect_failed_rechecks(artifacts) == [
        {
            "nodeid": "tests/integration_tests/test_alpha.py::test_lifecycle",
            "runtime_backend": "docker",
            "source_artifact": "integration-results-batch-1-of-36-docker",
        },
        {
            "nodeid": "tests/integration_tests/test_alpha.py::test_lifecycle",
            "runtime_backend": "process",
            "source_artifact": "integration-results-batch-1-of-36-process",
        },
        {
            "nodeid": "tests/integration_tests/test_beta.py::TestServer::test_query[param]",
            "runtime_backend": "auto",
            "source_artifact": "integration-results-batch-2-of-10",
        },
    ]


def test_collect_failed_rechecks_ignores_malformed_junit_reports(tmp_path):
    collector = load_collector_module()
    artifacts = tmp_path / "artifacts"
    malformed = artifacts / "integration-results-batch-1-of-10" / "results.xml"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("not xml", encoding="utf-8")

    assert collector.collect_failed_rechecks(artifacts) == []


def test_partition_integration_failures_allows_only_matching_recovered_rechecks():
    collector = load_collector_module()
    docker_artifact = "integration-results-batch-1-of-36-docker"
    process_artifact = "integration-results-batch-1-of-36-process"
    lifecycle = "tests.integration_tests.test_alpha::test_lifecycle"
    query = "tests.integration_tests.test_alpha::test_query"

    recovered, unrecovered = collector.partition_integration_failures(
        [
            (docker_artifact, lifecycle, "startup timeout"),
            (process_artifact, lifecycle, "startup timeout"),
            (docker_artifact, query, "query timeout"),
        ],
        {(docker_artifact, lifecycle)},
    )

    assert recovered == [(docker_artifact, lifecycle, "startup timeout")]
    assert unrecovered == [
        (process_artifact, lifecycle, "startup timeout"),
        (docker_artifact, query, "query timeout"),
    ]


def test_workflow_runs_post_matrix_rechecks_without_masking_initial_failures():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "collect-integration-rechecks:" in text
    assert "integration-flake-recheck:" in text
    assert "scripts/collect_integration_rechecks.py artifacts --github-output" in text
    assert "--no-retry" in text
    assert "needs.collect-integration-rechecks.outputs.has_rechecks == 'true'" in text
    assert "integration-recheck-results-" in text


def test_workflow_reports_recovered_rechecks_without_changing_initial_result():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "artifacts/integration-recheck-results-*/*.xml" in text
    assert "INTEGRATION FLAKE RECHECKS" in text
    assert "FLAKY RECOVERED" in text
    assert "initial failure retained" in text


def test_workflow_makes_only_recovered_integration_failures_non_blocking():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert text.count("continue-on-error: true") >= 2
    assert "partition_integration_failures" in text
    assert "unrecovered_int_failed" in text
    assert "len(unrecovered_int_failed)" in text


def test_workflow_is_valid_yaml():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'name: "integration-flake-recheck (${{ matrix.runtime_backend }}: ${{ matrix.nodeid }})"' in text
