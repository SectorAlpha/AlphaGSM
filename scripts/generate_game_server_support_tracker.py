#!/usr/bin/env python3
"""Generate the checked-in game server support tracker from TEST_STATUS.md."""

from __future__ import annotations

from pathlib import Path
import sys


SECTIONS = (
    ("PASSED", "Supported Now", "[x]"),
    ("ENABLED (AUTH)", "Supported Now", "[x]"),
    ("ENABLED (BYO)", "Supported Now", "[x]"),
    ("DISABLED", "Not Currently Supported", "[ ]"),
    ("SKIPPED", "Waiting On Prerequisites Or Validation", "[ ]"),
)
IGNORED_ENTRIES = {"archive_backed_installs"}
GATE_FILE_SECTIONS = (
    ("DISABLED", "disabled_servers.conf"),
    ("ENABLED (BYO)", "enabled_byo_servers.conf"),
    ("ENABLED (AUTH)", "enabled_auth_servers.conf"),
)


class SupportTrackerValidationError(RuntimeError):
    """Raised when TEST_STATUS.md drifts from the live support gate files."""


def parse_status_sections(status_text: str) -> dict[str, list[str]]:
    rows = {name: [] for name, _title, _checkbox in SECTIONS}
    current_section: str | None = None

    for line in status_text.splitlines():
        if line.startswith("## "):
            current_section = None
            for name, _title, _checkbox in SECTIONS:
                if line.startswith(f"## {name} "):
                    current_section = name
                    break
            continue

        if current_section is None or not line.startswith("|"):
            continue
        if "---" in line or "Test |" in line or "Skip reason" in line or "Type |" in line:
            continue

        parts = [part.strip() for part in line.strip("|").split("|")]
        if not parts or not parts[0] or parts[0] in IGNORED_ENTRIES:
            continue
        rows[current_section].append(parts[0])

    return rows


def parse_summary_counts(status_text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    in_summary = False

    for line in status_text.splitlines():
        if line.startswith("## "):
            in_summary = line.startswith("## Summary")
            continue

        if not in_summary or not line.startswith("|"):
            continue
        if "---" in line or "Status" in line:
            continue

        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue
        try:
            counts[parts[0]] = int(parts[1])
        except ValueError:
            continue

    return counts


def render_support_tracker(rows: dict[str, list[str]]) -> str:
    lines = [
        "# Game Server Support Tracker",
        "",
        "This page is a quick checkbox view of the current AlphaGSM server-support",
        "snapshot.",
        "",
        "This file is auto-generated from [TEST_STATUS.md](TEST_STATUS.md).",
        "Do not edit it by hand; re-run `python3 scripts/generate_game_server_support_tracker.py`.",
        "",
        "Source of truth:",
        "",
        "- [Integration Test Status](TEST_STATUS.md)",
        "",
        "Notes:",
        "",
        "- This page is meant for quick scanning.",
        "- Detailed reasons, caveats, and per-server notes stay in [TEST_STATUS.md](TEST_STATUS.md).",
        "- Non-server test-harness entries such as `archive_backed_installs` are intentionally omitted here.",
        "",
        "## Legend",
        "",
        "- `[x]` currently supported in the latest published test-status snapshot",
        "- `[ ]` not currently supported yet, or still waiting on prerequisites / validation",
    ]

    for name, title, checkbox in SECTIONS:
        lines.extend(["", f"## {title}", ""])
        for entry in rows[name]:
            lines.append(f"- {checkbox} {entry}")

    lines.append("")
    return "\n".join(lines)


def tracker_entry_for_module(module_name: str) -> str:
    """Map a module id from gate files to the tracker/test-status row id."""

    return str(module_name).strip().replace(".", "_")


def _load_gate_modules(path: Path) -> list[str]:
    modules = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        modules.append(line.split("\t", 1)[0].strip())
    return modules


def validate_support_tracker_state(repo_root: Path) -> None:
    """Ensure docs/TEST_STATUS.md matches the live enabled/disabled gate files."""

    status_path = repo_root / "docs" / "TEST_STATUS.md"
    status_text = status_path.read_text(encoding="utf-8")
    rows = parse_status_sections(status_text)
    summary_counts = parse_summary_counts(status_text)
    errors: list[str] = []

    disabled_modules = set(_load_gate_modules(repo_root / "disabled_servers.conf"))
    enabled_byo_modules = set(_load_gate_modules(repo_root / "enabled_byo_servers.conf"))
    enabled_auth_modules = set(_load_gate_modules(repo_root / "enabled_auth_servers.conf"))

    overlap = sorted(disabled_modules & (enabled_byo_modules | enabled_auth_modules))
    if overlap:
        errors.append(
            "Modules listed in both disabled and enabled gate files: "
            + ", ".join(overlap)
        )

    for section_name, row_names in rows.items():
        expected = len(row_names)
        actual = summary_counts.get(section_name)
        if actual is None:
            errors.append(f"Summary count missing for {section_name}")
        elif actual != expected:
            errors.append(
                f"Summary count mismatch for {section_name}: summary says {actual}, rows say {expected}"
            )

    for section_name, filename in GATE_FILE_SECTIONS:
        tracker_modules = {str(name).strip() for name in rows.get(section_name, [])}
        gate_modules = {
            tracker_entry_for_module(name) for name in _load_gate_modules(repo_root / filename)
        }
        if tracker_modules != gate_modules:
            missing_from_tracker = sorted(gate_modules - tracker_modules)
            missing_from_gate = sorted(tracker_modules - gate_modules)
            details = []
            if missing_from_tracker:
                details.append(
                    "missing from TEST_STATUS.md: " + ", ".join(missing_from_tracker)
                )
            if missing_from_gate:
                details.append(
                    "missing from " + filename + ": " + ", ".join(missing_from_gate)
                )
            errors.append(f"{section_name} mismatch ({'; '.join(details)})")

    if errors:
        raise SupportTrackerValidationError("\n".join(errors))


def main(argv: list[str]) -> int:
    check_mode = "--check" in argv
    repo_root = Path(__file__).resolve().parents[1]
    status_path = repo_root / "docs" / "TEST_STATUS.md"
    tracker_path = repo_root / "docs" / "game-server-support.md"

    rows = parse_status_sections(status_path.read_text(encoding="utf-8"))
    tracker_text = render_support_tracker(rows)
    try:
        validate_support_tracker_state(repo_root)
    except SupportTrackerValidationError as exc:
        print(f"Support tracker state is inconsistent:\n{exc}")
        return 1

    if check_mode:
        current_text = tracker_path.read_text(encoding="utf-8") if tracker_path.exists() else ""
        if current_text != tracker_text:
            print(
                "Game server support tracker is stale. "
                "Re-run scripts/generate_game_server_support_tracker.py"
            )
            return 1
        return 0

    tracker_path.write_text(tracker_text, encoding="utf-8")
    print(tracker_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
