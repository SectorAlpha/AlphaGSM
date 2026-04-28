"""Generated parity rows for canonical AlphaGSM game modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


UNIMPLEMENTED_STATUS_MARKERS = (
    "status is not implemented yet",
    "print_unsupported_message",
)


@dataclass(frozen=True)
class ModuleParityRow:
    canonical_id: str
    aliases: tuple[str, ...]
    support_state: str
    contract_complete: bool
    runtime_verified: bool
    missing_surfaces: tuple[str, ...]


def build_module_parity_rows(*, catalog, repo_root: Path) -> list[ModuleParityRow]:
    rows = []
    alias_map: dict[str, list[str]] = {}
    for alias, canonical in catalog.aliases.items():
        alias_map.setdefault(canonical, []).append(alias)

    disabled = _load_disabled_modules(repo_root / "disabled_servers.conf")

    for module_name in catalog.canonical_modules:
        source = _module_source(repo_root, module_name)
        missing = []
        lowered = source.lower()
        if any(marker in lowered for marker in UNIMPLEMENTED_STATUS_MARKERS):
            missing.append("status")
        if "def get_runtime_requirements(" not in source:
            missing.append("runtime_requirements")
        if "def get_container_spec(" not in source:
            missing.append("container_spec")

        rows.append(
            ModuleParityRow(
                canonical_id=module_name,
                aliases=tuple(sorted(alias_map.get(module_name, ()))),
                support_state="disabled" if module_name in disabled else "active",
                contract_complete=(len(missing) == 0),
                runtime_verified=(module_name not in disabled),
                missing_surfaces=tuple(missing),
            )
        )
    return rows


def render_markdown_report(rows: list[ModuleParityRow]) -> str:
    lines = [
        "# Module Parity Report",
        "",
        "| Canonical module | Aliases | Support state | Contract complete | Runtime verified | Missing surfaces |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {name} | {aliases} | {support} | {contract} | {runtime} | {missing} |".format(
                name=row.canonical_id,
                aliases=", ".join(row.aliases) or "-",
                support=row.support_state,
                contract="yes" if row.contract_complete else "no",
                runtime="yes" if row.runtime_verified else "no",
                missing=", ".join(row.missing_surfaces) or "-",
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_json_report(rows: list[ModuleParityRow]) -> str:
    return json.dumps([asdict(row) for row in rows], indent=2, sort_keys=True) + "\n"


def _module_source(repo_root: Path, module_name: str) -> str:
    path = repo_root / "src" / "gamemodules" / Path(*module_name.split("."))
    return path.with_suffix(".py").read_text(encoding="utf-8")


def _load_disabled_modules(path: Path) -> set[str]:
    disabled = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        disabled.add(line.split("\t", 1)[0].strip())
    return disabled
