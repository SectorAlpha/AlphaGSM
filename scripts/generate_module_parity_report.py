#!/usr/bin/env python3
"""Generate the checked-in canonical module parity reports."""

from __future__ import annotations

from pathlib import Path
import sys

from server.module_catalog import load_default_module_catalog
from server.module_parity import (
    build_module_parity_rows,
    render_json_report,
    render_markdown_report,
)


def main(argv: list[str]) -> int:
    check_mode = "--check" in argv
    repo_root = Path(__file__).resolve().parents[1]
    catalog = load_default_module_catalog()
    rows = build_module_parity_rows(catalog=catalog, repo_root=repo_root)

    md_path = repo_root / "docs" / "module_parity_report.md"
    json_path = repo_root / "docs" / "module_parity_report.json"
    md_text = render_markdown_report(rows)
    json_text = render_json_report(rows)

    if check_mode:
        current_md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        current_json = json_path.read_text(encoding="utf-8") if json_path.exists() else ""
        if current_md != md_text or current_json != json_text:
            print("Module parity report is stale. Re-run scripts/generate_module_parity_report.py")
            return 1
        return 0

    md_path.write_text(md_text, encoding="utf-8")
    json_path.write_text(json_text, encoding="utf-8")
    print(md_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
