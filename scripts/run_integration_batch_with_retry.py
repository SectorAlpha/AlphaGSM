#!/usr/bin/env python3
"""Run an integration-test shard and retry only failing cases once."""

from __future__ import annotations

import argparse
import copy
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="+", help="Integration test files or node ids to run")
    parser.add_argument("--results-file", default="results.xml")
    parser.add_argument("--retry-results-file", default="results-retry.xml")
    return parser.parse_args()


def pytest_nodeid_from_testcase(testcase: ET.Element) -> str:
    classname = testcase.attrib.get("classname", "")
    name = testcase.attrib.get("name", "")
    if not classname:
        return name

    parts = classname.split(".")
    module_index = next((index for index, part in enumerate(parts) if part.startswith("test_")), None)
    if module_index is None:
        module_parts = parts
        class_parts: list[str] = []
    else:
        module_parts = parts[: module_index + 1]
        class_parts = parts[module_index + 1 :]

    segments: list[str] = []
    if module_parts:
        segments.append("/".join(module_parts) + ".py")
    segments.extend(class_parts)
    if name:
        segments.append(name)
    return "::".join(segments)


def load_junit_root(xml_path: Path) -> ET.Element | None:
    if not xml_path.exists():
        return None
    try:
        return ET.parse(xml_path).getroot()
    except ET.ParseError:
        return None


def failing_test_nodeids(xml_path: Path) -> list[str]:
    root = load_junit_root(xml_path)
    if root is None:
        return []

    nodeids: list[str] = []
    seen: set[str] = set()
    for testcase in root.iter("testcase"):
        if testcase.find("failure") is None and testcase.find("error") is None:
            continue
        nodeid = pytest_nodeid_from_testcase(testcase)
        if nodeid and nodeid not in seen:
            seen.add(nodeid)
            nodeids.append(nodeid)
    return nodeids


def testcase_counts(testcases: list[ET.Element]) -> dict[str, int]:
    counts = {"tests": len(testcases), "failures": 0, "errors": 0, "skipped": 0}
    for testcase in testcases:
        if testcase.find("failure") is not None:
            counts["failures"] += 1
        elif testcase.find("error") is not None:
            counts["errors"] += 1
        elif testcase.find("skipped") is not None:
            counts["skipped"] += 1
    return counts


def write_junit_report(destination: Path, testcases: list[ET.Element]) -> None:
    counts = testcase_counts(testcases)
    suite = ET.Element(
        "testsuite",
        attrib={key: str(value) for key, value in counts.items()},
    )
    suite.set("name", "integration-test-retry")
    for testcase in testcases:
        suite.append(testcase)
    ET.ElementTree(suite).write(destination, encoding="utf-8", xml_declaration=True)


def merge_junit_reports(initial_report: Path, retry_report: Path, destination: Path) -> None:
    retry_root = load_junit_root(retry_report)
    if retry_root is None:
        if initial_report.exists() and initial_report != destination:
            shutil.copyfile(initial_report, destination)
        return

    initial_root = load_junit_root(initial_report)
    if initial_root is None:
        if retry_report != destination:
            shutil.copyfile(retry_report, destination)
        return

    initial_cases = [copy.deepcopy(testcase) for testcase in initial_root.iter("testcase")]
    retry_cases = {
        pytest_nodeid_from_testcase(testcase): copy.deepcopy(testcase)
        for testcase in retry_root.iter("testcase")
    }

    merged_cases: list[ET.Element] = []
    seen: set[str] = set()
    for testcase in initial_cases:
        nodeid = pytest_nodeid_from_testcase(testcase)
        if nodeid in retry_cases:
            merged_cases.append(retry_cases[nodeid])
        else:
            merged_cases.append(testcase)
        seen.add(nodeid)

    for nodeid, testcase in retry_cases.items():
        if nodeid not in seen:
            merged_cases.append(testcase)

    write_junit_report(destination, merged_cases)


def run_pytest(targets: list[str], results_file: Path) -> int:
    command = [sys.executable, "-m", "pytest", "-rs", f"--junit-xml={results_file}", *targets]
    return subprocess.run(command, check=False).returncode


def main() -> int:
    args = parse_args()
    results_file = Path(args.results_file)
    retry_results_file = Path(args.retry_results_file)
    for path in (results_file, retry_results_file):
        if path.exists():
            path.unlink()

    first_exit = run_pytest(args.tests, results_file)
    if first_exit == 0:
        return 0

    retry_targets = failing_test_nodeids(results_file)
    isolated_retry = bool(retry_targets)
    if isolated_retry:
        print(f"Retrying {len(retry_targets)} failed integration test(s):")
        for target in retry_targets:
            print(f"  RETRY {target}")
    else:
        retry_targets = list(args.tests)
        print("Could not isolate failing tests from JUnit XML; retrying the full shard once.")

    retry_exit = run_pytest(retry_targets, retry_results_file)
    if isolated_retry:
        merge_junit_reports(results_file, retry_results_file, results_file)
    elif retry_results_file.exists():
        shutil.copyfile(retry_results_file, results_file)

    return retry_exit


if __name__ == "__main__":
    raise SystemExit(main())