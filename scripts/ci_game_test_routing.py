#!/usr/bin/env python3
"""Route Linux game smoke and integration coverage based on changed files."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_TEST_DIR = REPO_ROOT / "tests" / "smoke_tests"
INTEGRATION_TEST_DIR = REPO_ROOT / "tests" / "integration_tests"
GAME_MODULE_DIR = REPO_ROOT / "src" / "gamemodules"
FULL_RUN_MODE = "all"
SKIP_MODE = "skip"
TARGETED_MODE = "targeted"
DOC_BASENAMES = {"README.md", "DEVELOPERS.md", "SKILLS.md"}
SLOW_TESTS = [
    "test_rs2server.py",
    "test_scumserver.py",
    "test_sevendaystodie.py",
    "test_palworld.py",
    "test_rust.py",
    "test_arksurvivalascended.py",
    "test_btserver.py",
    "test_enshrouded.py",
    "test_readyornotserver.py",
    "test_valheim.py",
]
MODULE_ALIASES = {
    "cs2server": ["counterstrike2"],
    "csgoserver": ["counterstrikeglobaloffensive"],
    "csgo": ["counterstrikeglobaloffensive"],
    "risingstorm2vietnam": ["rs2server"],
    "tf2server": ["teamfortress2"],
}


def normalize_repo_path(path: str) -> str:
    return PurePosixPath(path.strip()).as_posix()


def is_docs_only_path(path: str) -> bool:
    posix_path = PurePosixPath(normalize_repo_path(path))

    if not posix_path.parts:
        return False
    if posix_path.parts[0] in {"docs", "skills"}:
        return True
    if posix_path.name in DOC_BASENAMES:
        return True
    if posix_path.parts[0] == "docker" and posix_path.suffix == ".md":
        return True
    return False


def is_module_candidate(path: str) -> bool:
    posix_path = PurePosixPath(normalize_repo_path(path))
    return (
        len(posix_path.parts) >= 3
        and posix_path.parts[0] == "src"
        and posix_path.parts[1] == "gamemodules"
        and posix_path.suffix == ".py"
    )


def module_key_from_path(path: str) -> str:
    posix_path = PurePosixPath(normalize_repo_path(path))
    rel_parts = posix_path.parts[2:]
    return "_".join(PurePosixPath(*rel_parts).with_suffix("").parts)


def file_is_ambiguous_module_support(path: str) -> bool:
    posix_path = PurePosixPath(normalize_repo_path(path))
    return posix_path.name in {"__init__.py", "DEFAULT.py", "common.py"}


def candidate_names_for_module(path: str) -> list[str]:
    key = module_key_from_path(path)
    names = [key]
    names.extend(MODULE_ALIASES.get(key, []))
    seen: set[str] = set()
    ordered = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def resolve_module_targets(path: str, repo_root: Path | None = None) -> dict[str, list[str]] | None:
    root = repo_root or REPO_ROOT
    smoke_matches: list[str] = []
    integration_matches: list[str] = []

    if file_is_ambiguous_module_support(path):
        return None

    for candidate in candidate_names_for_module(path):
        smoke_path = root / "tests" / "smoke_tests" / f"run_{candidate}.sh"
        integration_path = root / "tests" / "integration_tests" / f"test_{candidate}.py"
        if smoke_path.exists():
            smoke_matches.append(smoke_path.relative_to(root).as_posix())
        if integration_path.exists():
            integration_matches.append(integration_path.relative_to(root).as_posix())

    if not smoke_matches and not integration_matches:
        return None

    return {
        "smoke_scripts": dedupe(smoke_matches),
        "integration_tests": dedupe(integration_matches),
    }


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def classify_changed_files(changed_files: list[str], repo_root: Path | None = None) -> dict[str, object]:
    root = repo_root or REPO_ROOT
    normalized = dedupe([normalize_repo_path(path) for path in changed_files if path.strip()])
    non_docs = [path for path in normalized if not is_docs_only_path(path)]

    if not non_docs:
        return {
            "mode": SKIP_MODE,
            "smoke_scripts": [],
            "integration_tests": [],
            "changed_files": normalized,
        }

    if any(not is_module_candidate(path) for path in non_docs):
        return {
            "mode": FULL_RUN_MODE,
            "smoke_scripts": [],
            "integration_tests": [],
            "changed_files": normalized,
        }

    selected_smoke: list[str] = []
    selected_integration: list[str] = []
    for path in non_docs:
        targets = resolve_module_targets(path, repo_root=root)
        if targets is None:
            return {
                "mode": FULL_RUN_MODE,
                "smoke_scripts": [],
                "integration_tests": [],
                "changed_files": normalized,
            }
        selected_smoke.extend(targets["smoke_scripts"])
        selected_integration.extend(targets["integration_tests"])

    return {
        "mode": TARGETED_MODE,
        "smoke_scripts": dedupe(selected_smoke),
        "integration_tests": dedupe(selected_integration),
        "changed_files": normalized,
    }


def build_smoke_matrix(selected_scripts: list[str] | None = None, repo_root: Path | None = None) -> dict[str, list[dict[str, str]]]:
    root = repo_root or REPO_ROOT
    scripts = selected_scripts
    if scripts is None:
        scripts = sorted(
            path.relative_to(root).as_posix()
            for path in (root / "tests" / "smoke_tests").glob("run_*.sh")
            if not path.name.startswith("run_backend_")
        )
        max_jobs = 40
        batch_size = max(1, math.ceil(len(scripts) / max_jobs))
        include = []
        total = math.ceil(len(scripts) / batch_size)
        for index in range(0, len(scripts), batch_size):
            chunk = scripts[index : index + batch_size]
            batch_number = index // batch_size + 1
            include.append(
                {
                    "batch": batch_number,
                    "scripts": " ".join(chunk),
                    "label": f"batch-{batch_number}-of-{total}",
                }
            )
        return {"include": include}

    include = []
    for index, script in enumerate(sorted(selected_scripts), start=1):
        include.append(
            {
                "batch": index,
                "scripts": script,
                "label": PurePosixPath(script).stem.replace("run_", ""),
            }
        )
    return {"include": include}


def build_integration_matrix(selected_tests: list[str] | None = None, repo_root: Path | None = None) -> dict[str, list[dict[str, str]]]:
    root = repo_root or REPO_ROOT
    if selected_tests is not None:
        include = []
        for index, test_file in enumerate(sorted(selected_tests), start=1):
            include.append(
                {
                    "batch": index,
                    "files": test_file,
                    "label": PurePosixPath(test_file).stem.replace("test_", ""),
                }
            )
        return {"include": include}

    all_tests = sorted(
        path.name for path in (root / "tests" / "integration_tests").glob("test_*.py")
    )
    slow_set = set(SLOW_TESTS)
    regular_tests = [test_name for test_name in all_tests if test_name not in slow_set]

    include = []
    for test_name in SLOW_TESTS:
        if test_name in all_tests:
            include.append(
                {
                    "batch": len(include) + 1,
                    "files": f"tests/integration_tests/{test_name}",
                    "label": f"slow-{test_name[5:-3]}",
                }
            )

    if regular_tests:
        max_jobs = 40
        batch_size = max(1, math.ceil(len(regular_tests) / max_jobs))
        total = math.ceil(len(regular_tests) / batch_size)
        for index in range(0, len(regular_tests), batch_size):
            chunk = regular_tests[index : index + batch_size]
            batch_number = index // batch_size + 1
            include.append(
                {
                    "batch": len(include) + 1,
                    "files": " ".join(f"tests/integration_tests/{name}" for name in chunk),
                    "label": f"batch-{batch_number}-of-{total}",
                }
            )

    return {"include": include}


def git_changed_files(base_sha: str, head_sha: str, repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    result = subprocess.run(
        ["git", "diff", "--name-only", base_sha, head_sha],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def write_github_outputs(outputs: dict[str, str], github_output: str) -> None:
    with open(github_output, "a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={value}\n")


def build_outputs_for_changed_files(changed_files: list[str], repo_root: Path | None = None) -> dict[str, str]:
    classification = classify_changed_files(changed_files, repo_root=repo_root)
    mode = classification["mode"]
    if mode == SKIP_MODE:
        smoke_matrix = {"include": []}
        integration_matrix = {"include": []}
    elif mode == TARGETED_MODE:
        smoke_matrix = build_smoke_matrix(classification["smoke_scripts"], repo_root=repo_root)
        integration_matrix = build_integration_matrix(
            classification["integration_tests"], repo_root=repo_root
        )
    else:
        smoke_matrix = build_smoke_matrix(repo_root=repo_root)
        integration_matrix = build_integration_matrix(repo_root=repo_root)

    return {
        "game_test_mode": mode,
        "has_smoke_tests": str(bool(smoke_matrix["include"])).lower(),
        "has_integration_tests": str(bool(integration_matrix["include"])).lower(),
        "smoke_matrix": json.dumps(smoke_matrix),
        "integration_matrix": json.dumps(integration_matrix),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed_files = git_changed_files(args.base_sha, args.head_sha, repo_root=REPO_ROOT)
    outputs = build_outputs_for_changed_files(changed_files, repo_root=REPO_ROOT)
    if args.github_output:
        write_github_outputs(outputs, args.github_output)
    else:
        print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
