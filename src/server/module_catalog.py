"""Canonical game-module catalog and alias resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


class ModuleCatalogError(RuntimeError):
    """Raised when the module catalog is invalid."""


@dataclass(frozen=True)
class ModuleCatalog:
    canonical_modules: tuple[str, ...]
    aliases: dict[str, str]
    namespace_defaults: dict[str, str]

    @classmethod
    def from_paths(cls, *, gamemodule_dir: Path, alias_path: Path) -> "ModuleCatalog":
        payload = json.loads(alias_path.read_text(encoding="utf-8"))
        canonical_modules = tuple(
            sorted(
                _canonical_module_names(
                    gamemodule_dir,
                    namespace_modules=set(payload.get("namespace_defaults", {})),
                )
            )
        )
        catalog = cls(
            canonical_modules=canonical_modules,
            aliases=dict(payload.get("aliases", {})),
            namespace_defaults=dict(payload.get("namespace_defaults", {})),
        )
        catalog.validate()
        return catalog

    def validate(self) -> None:
        canonical = set(self.canonical_modules)

        for key, value in self.aliases.items():
            if value not in canonical:
                raise ModuleCatalogError(f"Alias {key!r} points at non-module {value!r}")
            if value in self.aliases:
                raise ModuleCatalogError(f"Alias {key!r} points at alias target {value!r}")
            if key in canonical and key != value:
                raise ModuleCatalogError(
                    f"Alias key {key!r} shadows real module {key!r} but resolves to {value!r}"
                )

        for key, value in self.namespace_defaults.items():
            if value not in canonical:
                raise ModuleCatalogError(
                    f"Namespace default {key!r} points at non-module {value!r}"
                )

    def resolve(self, name: str) -> str:
        normalized = str(name).strip()
        if normalized in self.aliases:
            return self.aliases[normalized]
        if normalized in self.namespace_defaults:
            return self.namespace_defaults[normalized]
        return normalized


def _canonical_module_names(
    gamemodule_dir: Path, *, namespace_modules: set[str] | None = None
) -> list[str]:
    helper_modules = {
        "factorio",
        "minecraft.jardownload",
        "minecraft.properties_config",
        "minecraft.papermc",
        "terraria.common",
    }
    namespace_modules = namespace_modules or set()
    package_modules = {
        ".".join(path.relative_to(gamemodule_dir).parent.parts)
        for path in sorted(gamemodule_dir.rglob("__init__.py"))
        if ".".join(path.relative_to(gamemodule_dir).parent.parts) not in namespace_modules
    }
    names = set()
    for path in sorted(gamemodule_dir.rglob("*.py")):
        if path.name == "__init__.py":
            module_name = ".".join(path.relative_to(gamemodule_dir).parent.parts)
            if module_name in namespace_modules:
                continue
            if any(
                package_name != module_name and module_name.startswith(package_name + ".")
                for package_name in package_modules
            ):
                continue
        else:
            module_name = ".".join(path.relative_to(gamemodule_dir).with_suffix("").parts)
            if any(
                module_name == package_name or module_name.startswith(package_name + ".")
                for package_name in package_modules
            ):
                continue
        if module_name in helper_modules:
            continue
        source = path.read_text(encoding="utf-8")
        if "ALIAS_TARGET =" in source:
            continue
        names.add(module_name)
    return sorted(names)


def load_default_module_catalog() -> ModuleCatalog:
    root = Path(__file__).resolve().parents[1]
    return ModuleCatalog.from_paths(
        gamemodule_dir=root / "gamemodules",
        alias_path=Path(__file__).resolve().with_name("module_aliases.json"),
    )
