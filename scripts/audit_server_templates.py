#!/usr/bin/env python3
"""Audit docs/server-templates filenames against module and guide config paths."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "docs" / "server-templates"
DOCS_ROOT = REPO_ROOT / "docs" / "servers"
MODULE_ROOT = REPO_ROOT / "src" / "gamemodules"
IGNORED_TEMPLATE_DIRS = {"_template"}
MODULE_PATH_KEYS = (
    "configfile",
    "settingsfile",
    "eventfile",
    "eventrulesfile",
    "connectionfile",
    "servercfg",
)
CONFIG_LINE_RE = re.compile(r"\*\*Config files?\*\*:")
BACKTICK_RE = re.compile(r"`([^`]+)`")
SETDEFAULT_RE = re.compile(
    r"server\.data\.setdefault\(\s*[\"'](?P<key>configfile|settingsfile|eventfile|eventrulesfile|connectionfile|servercfg)[\"']\s*,\s*[\"'](?P<value>[^\"']+)[\"']"
)
VALVE_ARG_RE = re.compile(r"(?P<key>config_subdir|config_default)\s*=\s*['\"](?P<value>[^'\"]+)['\"]")


@dataclass(frozen=True)
class Evidence:
    source: str
    path: str
    filename: str


@dataclass(frozen=True)
class Finding:
    template_dir: str
    actual_files: tuple[str, ...]
    expected_files: tuple[str, ...]
    reason: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "template_dir": self.template_dir,
            "actual_files": list(self.actual_files),
            "expected_files": list(self.expected_files),
            "reason": self.reason,
            "evidence": list(self.evidence),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--include-clean",
        action="store_true",
        help="Print template directories even when they have no findings.",
    )
    return parser.parse_args()


def normalize_filename(path_text: str) -> str:
    return Path(path_text.strip()).name


def iter_template_dirs() -> Iterable[Path]:
    for path in sorted(TEMPLATE_ROOT.iterdir()):
        if not path.is_dir() or path.name in IGNORED_TEMPLATE_DIRS:
            continue
        yield path


def collect_actual_files(template_dir: Path) -> tuple[str, ...]:
    files = []
    for path in sorted(template_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "README.txt":
            continue
        files.append(path.name)
    return tuple(files)


def collect_doc_evidence(template_name: str) -> list[Evidence]:
    doc_path = DOCS_ROOT / f"{template_name}.md"
    if not doc_path.exists():
        return []
    evidence = []
    for line in doc_path.read_text(errors="ignore").splitlines():
        if not CONFIG_LINE_RE.search(line):
            continue
        for match in BACKTICK_RE.findall(line):
            filename = normalize_filename(match)
            if not filename or filename.lower() == "source":
                continue
            evidence.append(Evidence("docs", doc_path.relative_to(REPO_ROOT).as_posix(), filename))
    return dedupe_evidence(evidence)


def collect_module_evidence(template_name: str) -> list[Evidence]:
    module_path = MODULE_ROOT / f"{template_name}.py"
    if not module_path.exists():
        return []
    text = module_path.read_text(errors="ignore")
    evidence: list[Evidence] = []

    for match in SETDEFAULT_RE.finditer(text):
        filename = normalize_filename(match.group("value"))
        evidence.append(Evidence("module", module_path.relative_to(REPO_ROOT).as_posix(), filename))

    valve_args = {match.group("key"): match.group("value") for match in VALVE_ARG_RE.finditer(text)}
    config_default = valve_args.get("config_default")
    if config_default:
        evidence.append(Evidence("module", module_path.relative_to(REPO_ROOT).as_posix(), normalize_filename(config_default)))

    return dedupe_evidence(evidence)


def dedupe_evidence(evidence: Iterable[Evidence]) -> list[Evidence]:
    seen: set[tuple[str, str, str]] = set()
    ordered: list[Evidence] = []
    for item in evidence:
        key = (item.source, item.path, item.filename)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def evaluate_template(template_dir: Path) -> tuple[list[Finding], list[str]]:
    template_name = template_dir.name
    actual_files = collect_actual_files(template_dir)
    doc_evidence = collect_doc_evidence(template_name)
    module_evidence = collect_module_evidence(template_name)
    evidence = doc_evidence + [item for item in module_evidence if item not in doc_evidence]
    expected_files = tuple(sorted({item.filename for item in evidence}))
    evidence_text = tuple(f"{item.source}:{item.path}:{item.filename}" for item in evidence)
    findings: list[Finding] = []

    if not actual_files:
        findings.append(
            Finding(template_name, actual_files, expected_files, "no template files present", evidence_text)
        )
        return findings, list(expected_files)

    if not expected_files:
        return findings, []

    actual_set = set(actual_files)
    expected_set = set(expected_files)

    if "alphagsm-example.cfg" in actual_set and expected_set:
        findings.append(
            Finding(
                template_name,
                actual_files,
                expected_files,
                "generic template filename still present despite config filename evidence",
                evidence_text,
            )
        )

    if actual_set.isdisjoint(expected_set):
        findings.append(
            Finding(
                template_name,
                actual_files,
                expected_files,
                "template filenames do not match any module- or docs-backed config filename",
                evidence_text,
            )
        )

    return findings, list(expected_files)


def render_text(findings: list[Finding], clean_dirs: list[tuple[str, list[str]]], include_clean: bool) -> str:
    lines: list[str] = []
    if findings:
        for finding in findings:
            lines.append(f"{finding.template_dir}: {finding.reason}")
            lines.append(f"  actual: {', '.join(finding.actual_files) if finding.actual_files else '(none)'}")
            lines.append(f"  expected: {', '.join(finding.expected_files) if finding.expected_files else '(none)'}")
            for item in finding.evidence:
                lines.append(f"  evidence: {item}")
    else:
        lines.append("No template filename mismatches found.")

    if include_clean:
        for template_name, expected in clean_dirs:
            summary = ", ".join(expected) if expected else "no config filename evidence"
            lines.append(f"CLEAN {template_name}: {summary}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []
    clean_dirs: list[tuple[str, list[str]]] = []

    for template_dir in iter_template_dirs():
        dir_findings, expected = evaluate_template(template_dir)
        if dir_findings:
            findings.extend(dir_findings)
        else:
            clean_dirs.append((template_dir.name, expected))

    if args.json:
        payload = {
            "findings": [item.as_dict() for item in findings],
            "clean": [
                {"template_dir": template_name, "expected_files": expected}
                for template_name, expected in clean_dirs
            ]
            if args.include_clean
            else [],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(findings, clean_dirs, args.include_clean))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())