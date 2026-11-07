#!/usr/bin/env python3
"""Insert schema-backed server variable tables into docs/servers/*.md."""

from __future__ import annotations

import os
import re
import sys
from importlib import import_module
from pathlib import Path

from server.module_catalog import ModuleCatalog
from server.settable_keys import SettingSpec, get_effective_aliases


REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE_DIR = REPO_ROOT / "docs" / "servers"
BEGIN = "<!-- alphagsm-server-variables:start -->"
END = "<!-- alphagsm-server-variables:end -->"
MARKER_RE = re.compile(
    re.escape(BEGIN) + r".*?" + re.escape(END),
    re.DOTALL,
)


def _catalog() -> ModuleCatalog:
    return ModuleCatalog.from_paths(
        gamemodule_dir=REPO_ROOT / "src" / "gamemodules",
        alias_path=REPO_ROOT / "src" / "server" / "module_aliases.json",
    )


def resolve_guide_module(path: Path, catalog: ModuleCatalog) -> str | None:
    """Return a canonical module id for a server guide, or None for alias stubs."""
    text = path.read_text(encoding="utf-8")
    if re.search(r"is an alias for", text, re.I):
        return None
    stem = path.stem
    candidates = (
        stem,
        stem.replace("-", "."),
        stem.replace("-", ""),
    )
    for candidate in candidates:
        resolved = catalog.resolve(candidate)
        if resolved in catalog.canonical_modules:
            return resolved
    return None


def load_schema(module_id: str) -> dict[str, SettingSpec]:
    try:
        module = import_module("gamemodules." + module_id)
    except Exception as exc:  # pragma: no cover - defensive for odd modules
        print(f"skip {module_id}: import failed: {exc}", file=sys.stderr)
        return {}
    schema = getattr(module, "setting_schema", {}) or {}
    if not isinstance(schema, dict):
        return {}
    return {
        key: spec
        for key, spec in schema.items()
        if isinstance(spec, SettingSpec)
    }


def render_section(module_id: str, schema: dict[str, SettingSpec]) -> str:
    lines = [
        BEGIN,
        "",
        "## Server variables",
        "",
        f"After `create {module_id}`, inspect or change these with `set`:",
        "",
        "```bash",
        "alphagsm myserver set --list",
        "alphagsm myserver set KEY --describe",
        "alphagsm myserver set KEY VALUE",
        "```",
        "",
    ]
    if not schema:
        lines.extend(
            [
                "This module does not declare schema-backed keys. `set --list` after",
                "create is still the live source of truth.",
                "",
                END,
            ]
        )
        return "\n".join(lines)
    lines.extend(
        [
            "| Key | Aliases | Type | What it does |",
            "| --- | --- | --- | --- |",
        ]
    )
    for spec in sorted(schema.values(), key=lambda item: item.canonical_key):
        aliases = ", ".join(get_effective_aliases(spec, schema)) or "—"
        description = " ".join(spec.description.split()) if spec.description else "—"
        if spec.secret:
            description += " Stored as a secret."
        if spec.examples:
            description += f" Example: `{spec.examples[0]}`."
        lines.append(
            f"| `{spec.canonical_key}` | {aliases} | {spec.value_type} | {description} |"
        )
    lines.extend(["", END])
    return "\n".join(lines)


def apply_section(text: str, section: str) -> str:
    if MARKER_RE.search(text):
        return MARKER_RE.sub(section, text)
    if re.search(r"^## Developer Notes", text, re.M):
        return re.sub(r"^## Developer Notes", section + "\n\n## Developer Notes", text, count=1, flags=re.M)
    return text.rstrip() + "\n\n" + section + "\n"


def main() -> int:
    os.environ.setdefault(
        "ALPHAGSM_CONFIG_LOCATION",
        str(REPO_ROOT / "tests" / "alphagsm-test.conf"),
    )
    sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "src")]
    catalog = _catalog()
    updated = 0
    skipped = 0
    for path in sorted(GUIDE_DIR.glob("*.md")):
        module_id = resolve_guide_module(path, catalog)
        if module_id is None:
            skipped += 1
            continue
        schema = load_schema(module_id)
        section = render_section(module_id, schema)
        original = path.read_text(encoding="utf-8")
        rewritten = apply_section(original, section)
        if rewritten != original:
            path.write_text(rewritten, encoding="utf-8")
            updated += 1
    print(f"Updated {updated} server guides; skipped {skipped} alias/unmapped pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
