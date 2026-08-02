#!/usr/bin/env python3
"""Collect failed integration JUnit cases for post-matrix CI rechecks."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts_dir", type=Path)
    parser.add_argument("--github-output", type=Path)
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


def collect_failed_rechecks(artifacts_dir: Path) -> list[dict[str, str]]:
    """Return failed integration cases with their original runtime selection."""

    collected: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for report_path in sorted(artifacts_dir.glob("integration-results-*/*.xml")):
        try:
            root = ET.parse(report_path).getroot()
        except ET.ParseError:
            continue
        artifact_name = report_path.parent.name
        runtime_backend = runtime_backend_from_artifact(artifact_name)
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
                }
            )
    return collected


def main() -> int:
    args = parse_args()
    matrix = {"include": collect_failed_rechecks(args.artifacts_dir)}
    payload = json.dumps(matrix, separators=(",", ":"))
    print(payload)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write("matrix=" + payload + "\n")
            output.write("has_rechecks=" + str(bool(matrix["include"])).lower() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
