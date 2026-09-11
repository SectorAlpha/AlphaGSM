#!/usr/bin/env python3
"""List gamemodule files missing the config-sync contract."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
GAME_MODULE_ROOT = REPO_ROOT / "src" / "gamemodules"
GAME_CONFIG_HINTS = {
    '"port"',
    '"queryport"',
    '"maxplayers"',
    '"servername"',
    '"hostname"',
    '"map"',
    '"scenarioid"',
    '"gamemode"',
    '"difficulty"',
    '"levelname"',
}


def _manages_real_config(source: str) -> bool:
    return (
        'setdefault("configfile"' in source
        and "def checkvalue(" in source
        and any(hint in source for hint in GAME_CONFIG_HINTS)
        and (
            "updateconfig(" in source
            or "json.dump(" in source
            or "xml.etree" in source
            or "ElementTree" in source
            or "server.json" in source
        )
    )


def scan(repo_root: Path | str | None = None) -> list[dict[str, str]]:
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    game_module_root = root / "src" / "gamemodules"
    findings: list[dict[str, str]] = []

    for path in sorted(game_module_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        has_sync_function = "def sync_server_config(" in source
        has_config_sync_keys = (
            "config_sync_keys" in source or "set_sync_keys" in source
        )

        if has_sync_function and not has_config_sync_keys:
            findings.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "reason": "missing config_sync_keys for sync_server_config",
                }
            )
            continue

        if _manages_real_config(source) and not has_config_sync_keys:
            findings.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "reason": "manages real server config but missing config_sync_keys",
                }
            )

    return findings


def main(argv: list[str], repo_root: Path | str | None = None) -> int:
    del argv
    findings = scan(repo_root=repo_root)
    print(f"Found {len(findings)} modules missing config-sync contract coverage.")
    for finding in findings:
        print(f"{finding['path']} - {finding['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
