"""Tests for collecting post-matrix integration rechecks from JUnit artifacts."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

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


def test_collect_failed_rechecks_rejects_malformed_junit_reports(tmp_path):
    collector = load_collector_module()
    artifacts = tmp_path / "artifacts"
    malformed = artifacts / "integration-results-batch-1-of-10" / "results.xml"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("not xml", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed"):
        collector.collect_failed_rechecks(artifacts)


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


def test_workflow_retains_initial_exit_status_and_reports():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert text.count("continue-on-error: true") == 2
    assert text.count('"$test_exit" > exit-code.txt') == 2
    assert "scripts/summarize_tests.py artifacts" in text


def test_required_summary_covers_all_jobs_and_receives_needs_evidence():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    summary = text.split("  summarize-tests:", 1)[1]
    assert "if: always()" in summary
    assert "CI_NEEDS_JSON: ${{ toJson(needs) }}" in summary
    for job in ("lint", "unit-test", "coverage", "binary-build-smoke", "backend-smoke-test",
                "backend-integration-test", "windows-minecraft-integration", "macos-minecraft-integration"):
        assert job in summary.split("    needs: ", 1)[1].split("\n", 1)[0]
    assert summary.index("uses: actions/checkout@v4") < summary.index("scripts/summarize_tests.py")


def test_recheck_preserves_heavy_runner_and_registration_environment():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    recheck = text.split("  integration-flake-recheck:", 1)[1].split("  summarize-tests:", 1)[0]
    assert "matrix.runner_class == 'heavy'" in recheck
    assert "vars.ALPHAGSM_HEAVY_RUNNER_LABELS_JSON" in recheck
    assert "ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP: ${{ vars.ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP }}" in recheck
    assert "export ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP=" in recheck
    assert "ALPHAGSM_RECHECK_NODEID: ${{ matrix.nodeid }}" in recheck
    assert "--whitelist-environment=ALPHAGSM_RECHECK_NODEID" in recheck


def test_workflow_is_valid_yaml():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'name: "integration-recheck (${{ matrix.runtime_backend }}: ${{ matrix.nodeid }})"' in text


def test_collect_rechecks_preserves_runner_class_from_routing(tmp_path):
    collector = load_collector_module()
    artifact = 'integration-results-heavy-alpha-process'
    write_report(tmp_path / artifact / 'results.xml',
                 [('tests.integration_tests.test_alpha', 'test_lifecycle', 'failure')])
    routing = {'integration_heavy_matrix': '{"include":[{"label":"alpha-process","runtime_backend":"process"}]}',
               'integration_standard_matrix': '{"include":[]}'}
    rows = collector.collect_failed_rechecks(tmp_path, routing=routing)
    assert rows[0]['runner_class'] == 'heavy'
    assert rows[0]['runtime_backend'] == 'process'
