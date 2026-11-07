#!/usr/bin/env python3
"""Backfill missing defaults into AlphaGSM-oriented server templates."""

from __future__ import annotations

import argparse
import sys

from utils.server_template_defaults import (
    extract_template_defaults,
    iter_alphagsm_example_templates,
    merge_template_defaults,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report files that would change without writing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed = []

    for template_path in iter_alphagsm_example_templates():
        defaults = extract_template_defaults(template_path.parent.name)
        original = template_path.read_text(encoding="utf-8")
        updated = merge_template_defaults(original, defaults)
        if updated == original:
            continue
        changed.append(template_path)
        if not args.check:
            template_path.write_text(updated, encoding="utf-8")

    if changed:
        for path in changed:
            print(path.as_posix())
        return 1 if args.check else 0

    print("No AlphaGSM example templates needed updates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
