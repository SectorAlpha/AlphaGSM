"""Generated parity rows for canonical AlphaGSM game modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from server.capabilities import load_capability_inventory, load_support_states


UNIMPLEMENTED_STATUS_MARKERS = (
    "status is not implemented yet",
    "print_unsupported_message",
)


@dataclass(frozen=True)
class ModuleParityRow:  # pylint: disable=too-many-instance-attributes
    canonical_id: str
    aliases: tuple[str, ...]
    support_state: str
    contract_complete: bool
    runtime_verified: bool
    missing_surfaces: tuple[str, ...]
    runtime_family: str | None
    platforms: tuple[str, ...] | None
    architectures: tuple[str, ...] | None
    provider_categories: tuple[str, ...] | None


def build_module_parity_rows(*, catalog, repo_root: Path, capability_inventory=None) -> list[ModuleParityRow]:
    rows = []
    alias_map: dict[str, list[str]] = {}
    for alias, canonical in catalog.aliases.items():
        alias_map.setdefault(canonical, []).append(alias)

    states = load_support_states(repo_root, catalog)
    inventory = capability_inventory or load_capability_inventory()
    capabilities = {row["module"]: row for row in inventory["modules"]}

    for module_name in catalog.canonical_modules:
        source = _module_source(repo_root, module_name)
        missing = []
        lowered = source.lower()
        if any(marker in lowered for marker in UNIMPLEMENTED_STATUS_MARKERS):
            missing.append("status")
        if (
            "def get_runtime_requirements(" not in source
            and "get_runtime_requirements =" not in source
        ):
            missing.append("runtime_requirements")
        if "def get_container_spec(" not in source and "get_container_spec =" not in source:
            missing.append("container_spec")

        rows.append(
            ModuleParityRow(
                canonical_id=module_name,
                aliases=tuple(sorted(alias_map.get(module_name, ()))),
                support_state=states.get(module_name, "UNKNOWN"),
                contract_complete=(len(missing) == 0),
                runtime_verified=(states.get(module_name) == "PASSED"),
                missing_surfaces=tuple(missing),
                runtime_family=capabilities.get(module_name, {}).get("runtime", {}).get("family"),
                platforms=_declared_values(capabilities.get(module_name, {}), "platforms"),
                architectures=_declared_values(capabilities.get(module_name, {}), "architectures"),
                provider_categories=_declared_values(capabilities.get(module_name, {}), "provider_categories"),
            )
        )
    return rows


def _declared_values(capabilities, key):
    values = capabilities.get(key)
    return tuple(values) if values is not None else None


def render_markdown_report(rows: list[ModuleParityRow]) -> str:
    lines = [
        "# Module Parity Report",
        "",
        "Runtime verified reflects recorded PASSED tracker evidence; it is not a new validation run.",
        "Unknown platforms and architectures have no explicit declaration, even when a runtime hook exists.",
        "",
        "| Canonical module | Aliases | Support state | Contract complete | Runtime verified | Missing surfaces | Runtime family | Platforms | Architectures | Provider categories |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {name} | {aliases} | {support} | {contract} | {runtime} | {missing} | {family} | {platforms} | {architectures} | {providers} |".format(
                name=row.canonical_id,
                aliases=", ".join(row.aliases) or "-",
                support=row.support_state,
                contract="yes" if row.contract_complete else "no",
                runtime="yes" if row.runtime_verified else "no",
                missing=", ".join(row.missing_surfaces) or "-",
                family=row.runtime_family or "unknown",
                platforms=", ".join(row.platforms) if row.platforms is not None else "unknown",
                architectures=", ".join(row.architectures) if row.architectures is not None else "unknown",
                providers=", ".join(row.provider_categories) if row.provider_categories is not None else "unknown",
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_json_report(rows: list[ModuleParityRow]) -> str:
    return json.dumps([asdict(row) for row in rows], indent=2, sort_keys=True) + "\n"


def _module_source(repo_root: Path, module_name: str) -> str:
    source_path = _module_source_path(repo_root, module_name)
    if source_path.name == "__init__.py":
        return "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(source_path.parent.rglob("*.py"))
        )
    return source_path.read_text(encoding="utf-8")


def _module_source_path(repo_root: Path, module_name: str) -> Path:
    path = repo_root / "src" / "gamemodules" / Path(*module_name.split("."))
    package_init = path / "__init__.py"
    if package_init.exists():
        return package_init
    return path.with_suffix(".py")


def _load_disabled_modules(path: Path) -> set[str]:
    disabled = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        disabled.add(line.split("\t", 1)[0].strip())
    return disabled
