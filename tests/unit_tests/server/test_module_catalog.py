from pathlib import Path
import os
import subprocess as sp
import sys

import pytest

from server.module_catalog import ModuleCatalog, ModuleCatalogError


def write_alias_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "module_aliases.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_catalog_resolves_alias_and_namespace_default(tmp_path):
    alias_path = write_alias_file(
        tmp_path,
        """
        {
          "aliases": {
            "tf2": "teamfortress2",
            "tf2server": "teamfortress2"
          },
          "namespace_defaults": {
            "minecraft": "minecraft.vanilla"
          }
        }
        """,
    )

    catalog = ModuleCatalog.from_paths(
        gamemodule_dir=Path("src/gamemodules"),
        alias_path=alias_path,
    )

    assert catalog.resolve("tf2") == "teamfortress2"
    assert catalog.resolve("tf2server") == "teamfortress2"
    assert catalog.resolve("teamfortress2") == "teamfortress2"
    assert catalog.resolve("minecraft") == "minecraft.vanilla"


def test_catalog_rejects_alias_target_that_is_not_a_real_module(tmp_path):
    alias_path = write_alias_file(
        tmp_path,
        """
        {
          "aliases": {
            "tf2": "missing.module"
          },
          "namespace_defaults": {}
        }
        """,
    )

    with pytest.raises(ModuleCatalogError, match="missing.module"):
        ModuleCatalog.from_paths(
            gamemodule_dir=Path("src/gamemodules"),
            alias_path=alias_path,
        )


def test_catalog_rejects_alias_chain(tmp_path):
    alias_path = write_alias_file(
        tmp_path,
        """
        {
          "aliases": {
            "tf2": "tf2server",
            "tf2server": "teamfortress2"
          },
          "namespace_defaults": {}
        }
        """,
    )

    with pytest.raises(ModuleCatalogError, match="tf2server"):
        ModuleCatalog.from_paths(
            gamemodule_dir=Path("src/gamemodules"),
            alias_path=alias_path,
        )


def test_catalog_rejects_shadowed_name_when_it_points_elsewhere(tmp_path):
    alias_path = write_alias_file(
        tmp_path,
        """
        {
          "aliases": {
            "teamfortress2": "counterstrike2"
          },
          "namespace_defaults": {}
        }
        """,
    )

    with pytest.raises(ModuleCatalogError, match="teamfortress2"):
        ModuleCatalog.from_paths(
            gamemodule_dir=Path("src/gamemodules"),
            alias_path=alias_path,
        )


def test_module_catalog_import_does_not_require_alphagsm_config(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(("src", env.get("PYTHONPATH", ""))).rstrip(
        os.pathsep
    )
    env["ALPHAGSM_CONFIG_LOCATION"] = str(tmp_path / "missing-system.conf")
    env["ALPHAGSM_USERCONFIG_LOCATION"] = str(tmp_path / "missing-user.conf")

    result = sp.run(
        [sys.executable, "-c", "import server.module_catalog"],
        check=False,
        capture_output=True,
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
