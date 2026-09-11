#!/usr/bin/env python3
"""Collect failed integration JUnit cases for post-matrix CI rechecks."""

from __future__ import annotations

import argparse
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts_dir", type=Path)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--routing-json", default=os.environ.get("CI_ROUTING_JSON"))
    return parser.parse_args()


def pytest_nodeid_from_testcase(testcase: ET.Element) -> str:
    """Return the pytest node id represented by one JUnit testcase element."""

    classname = testcase.attrib.get("classname", "")
    name = testcase.attrib.get("name", "")
    if not classname:
        return name.replace(".", "/") + ".py" if name.startswith("tests.") else name

    parts = classname.split(".")
    module_index = next(
        (index for index, part in enumerate(parts) if part.startswith("test_")),
        None,
    )
    if module_index is None:
        module_parts, class_parts = parts, []
    else:
        module_parts, class_parts = parts[: module_index + 1], parts[module_index + 1 :]

    segments = ["/".join(module_parts) + ".py"] if module_parts else []
    segments.extend(class_parts)
    if name:
        segments.append(name)
    return "::".join(segments)


def runtime_backend_from_artifact(artifact_name: str) -> str:
    """Return the runtime setting that produced an integration artifact."""

    if artifact_name.endswith("-docker"):
        return "docker"
    if artifact_name.endswith("-process"):
        return "process"
    return "auto"


def collect_failed_rechecks(artifacts_dir: Path, routing: dict | None = None) -> list[dict[str, str]]:
    """Return failed integration cases with their original runtime selection."""

    sources = {}
    if routing is not None:
        for runner_class in ("standard", "heavy"):
            matrix = json.loads(routing[f"integration_{runner_class}_matrix"])
            for entry in matrix["include"]:
                artifact = f"integration-results-{runner_class}-{entry['label']}"
                sources[artifact] = {
                    "runner_class": runner_class,
                    "runtime_backend": entry.get("runtime_backend", "auto"),
                }
    collected: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for report_path in sorted(artifacts_dir.glob("integration-results-*/*.xml")):
        try:
            root = ET.parse(report_path).getroot()
        except ET.ParseError as exc:
            raise ValueError(f"Malformed JUnit report: {report_path}") from exc
        artifact_name = report_path.parent.name
        if routing is not None and artifact_name not in sources:
            raise ValueError(f"Unexpected integration artifact: {artifact_name}")
        runtime_backend = runtime_backend_from_artifact(artifact_name)
        metadata = sources.get(artifact_name, {})
        for testcase in root.iter("testcase"):
            if testcase.find("failure") is None and testcase.find("error") is None:
                continue
            nodeid = pytest_nodeid_from_testcase(testcase)
            key = (nodeid, runtime_backend, artifact_name)
            if not nodeid or key in seen:
                continue
            seen.add(key)
            collected.append(
                {
                    "nodeid": nodeid,
                    "runtime_backend": runtime_backend,
                    "source_artifact": artifact_name,
                    **metadata,
                }
            )
    return collected


def partition_integration_failures(
    initial_failures: list[tuple[str, str, str]],
    recheck_passes: set[tuple[str, str]],
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """Split initial failures into recovered and still-blocking cases."""

    recovered: list[tuple[str, str, str]] = []
    unrecovered: list[tuple[str, str, str]] = []
    for failure in initial_failures:
        source_artifact, nodeid, _reason = failure
        if (source_artifact, nodeid) in recheck_passes:
            recovered.append(failure)
        else:
            unrecovered.append(failure)
    return recovered, unrecovered


def main() -> int:
    args = parse_args()
    matrix = {"include": collect_failed_rechecks(
        args.artifacts_dir, json.loads(args.routing_json) if args.routing_json else None
    )}
    payload = json.dumps(matrix, separators=(",", ":"))
    print(payload)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write("matrix=" + payload + "\n")
            output.write("has_rechecks=" + str(bool(matrix["include"])).lower() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
