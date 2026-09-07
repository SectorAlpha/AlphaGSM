#!/usr/bin/env python3
"""Generate the checked-in canonical module parity reports."""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = str(REPO_ROOT / "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from server.module_catalog import load_default_module_catalog
from server.capabilities import build_capability_inventory, INVENTORY_PATH
from server.module_parity import (
    build_module_parity_rows,
    render_json_report,
    render_markdown_report,
)


def main(argv: list[str]) -> int:
    check_mode = "--check" in argv
    os.environ.setdefault("ALPHAGSM_CONFIG_LOCATION", os.devnull)
    os.environ.setdefault("ALPHAGSM_USERCONFIG_LOCATION", os.devnull)
    catalog = load_default_module_catalog()
    inventory = build_capability_inventory(catalog=catalog, repo_root=REPO_ROOT)
    inventory_text = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    rows = build_module_parity_rows(catalog=catalog, repo_root=REPO_ROOT, capability_inventory=inventory)

    md_path = REPO_ROOT / "docs" / "module_parity_report.md"
    json_path = REPO_ROOT / "docs" / "module_parity_report.json"
    md_text = render_markdown_report(rows)
    json_text = render_json_report(rows)

    if check_mode:
        current_md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        current_json = json_path.read_text(encoding="utf-8") if json_path.exists() else ""
        current_inventory = INVENTORY_PATH.read_text(encoding="utf-8") if INVENTORY_PATH.exists() else ""
        if current_md != md_text or current_json != json_text or current_inventory != inventory_text:
            print("Module parity report is stale. Re-run scripts/generate_module_parity_report.py")
            return 1
        return 0

    md_path.write_text(md_text, encoding="utf-8")
    json_path.write_text(json_text, encoding="utf-8")
    INVENTORY_PATH.write_text(inventory_text, encoding="utf-8")
    print(md_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
