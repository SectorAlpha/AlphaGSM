#!/usr/bin/env python3
"""Generate the checked-in game server support tracker from TEST_STATUS.md."""

from __future__ import annotations

from pathlib import Path
import sys


SECTIONS = (
    ("PASSED", "Supported Now", "[x]"),
    ("DISABLED", "Not Currently Supported", "[ ]"),
    ("SKIPPED", "Waiting On Prerequisites Or Validation", "[ ]"),
)
IGNORED_ENTRIES = {"archive_backed_installs"}


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


def main(argv: list[str]) -> int:
    check_mode = "--check" in argv
    repo_root = Path(__file__).resolve().parents[1]
    status_path = repo_root / "docs" / "TEST_STATUS.md"
    tracker_path = repo_root / "docs" / "game-server-support.md"

    rows = parse_status_sections(status_path.read_text(encoding="utf-8"))
    tracker_text = render_support_tracker(rows)

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