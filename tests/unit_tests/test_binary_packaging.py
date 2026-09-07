"""Standalone builds must retain dynamically loaded modules and their resources."""

import importlib
import os
from pathlib import Path
import subprocess
import sys

from scripts import build_binary


def test_binary_includes_every_game_package_source_and_resource():
    resources = dict(build_binary.collect_runtime_data())
    source_root = build_binary.REPO_ROOT / "src"
    for path in (source_root / "gamemodules").rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix == ".pyc":
            continue
        assert str(path) in resources, f"Missing runtime resource: {path}"
        assert resources[str(path)] == path.parent.relative_to(source_root).as_posix()


def test_binary_includes_docker_build_contexts_and_shared_resources():
    resources = dict(build_binary.collect_runtime_data())
    for family in ("java", "quake-linux", "service-console", "simple-tcp",
                   "steamcmd-linux", "wine-proton"):
        context = build_binary.REPO_ROOT / "docker" / family
        for path in context.iterdir():
            if path.is_file():
                assert resources[str(path)] == f"docker/{family}"
    for relative in ("server/module_aliases.json", "screen/screenrc_template.txt",
                     "utils/steamcmd_gamescript_template.txt"):
        path = build_binary.REPO_ROOT / "src" / relative
        assert str(path) in resources
    for relative in ("disabled_servers.conf", "enabled_byo_servers.conf", "enabled_auth_servers.conf",
                     "scripts/install_proton.sh", "scripts/select_proton_asset.py"):
        path = build_binary.REPO_ROOT / relative
        assert resources[str(path)] == path.parent.relative_to(build_binary.REPO_ROOT).as_posix()


def test_frozen_default_settings_need_no_adjacent_config(monkeypatch, tmp_path):
    from utils.settings import _settings
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "alphagsm"))
    monkeypatch.delenv("ALPHAGSM_CONFIG_LOCATION", raising=False)
    settings = object.__new__(_settings.Settings)
    assert not settings.system.getsection("core")


def test_frozen_explicit_missing_configuration_remains_an_error(monkeypatch, tmp_path):
    import pytest
    from utils.settings import _settings
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", str(tmp_path / "missing.conf"))
    settings = object.__new__(_settings.Settings)
    with pytest.raises(FileNotFoundError):
        _ = settings.system


def test_frozen_cli_version_boots_with_no_system_or_user_config(tmp_path):
    env = {key: value for key, value in os.environ.items() if not key.startswith("ALPHAGSM_")}
    env.update(HOME=str(tmp_path), USERPROFILE=str(tmp_path),
               LOCALAPPDATA=str(tmp_path), PYTHONPATH=str(build_binary.REPO_ROOT / "src"))
    result = subprocess.run([
        sys.executable, "-c",
        "import sys; sys.frozen = True; sys.executable = 'unused-alphagsm'; "
        "import core; raise SystemExit(core.main('alphagsm', ['--version']))",
    ], cwd=tmp_path, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("AlphaGSM ")


def test_binary_command_covers_all_packages_and_only_excludes_placeholder():
    args = build_binary.pyinstaller_arguments()
    packages = [args[index + 1] for index, arg in enumerate(args)
                if arg == "--collect-submodules"]
    assert set(packages) == {"core", "downloader", "downloadermodules", "gamemodules",
                             "screen", "server", "utils"}
    excluded = [args[index + 1] for index, arg in enumerate(args)
                if arg == "--exclude-module"]
    assert excluded == ["gamemodules.factorio"]


def test_frozen_catalog_has_the_same_canonical_modules(monkeypatch):
    from server import module_catalog
    source = module_catalog.load_default_module_catalog()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    frozen = module_catalog.load_default_module_catalog()
    assert frozen == source


def test_binary_signs_nested_macos_components_when_identity_is_configured(monkeypatch):
    monkeypatch.setenv("ALPHAGSM_CODESIGN_IDENTITY", "Developer ID Application: Example")
    args = build_binary.pyinstaller_arguments()
    assert args[args.index("--codesign-identity") + 1] == "Developer ID Application: Example"


def test_integration_binary_runs_directly_outside_checkout(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    binary = tmp_path / "alphagsm"
    config = tmp_path / "alphagsm.conf"
    monkeypatch.setenv("ALPHAGSM_BINARY", str(binary))
    monkeypatch.setenv("PYTHONPATH", "must-not-leak")
    env = helpers.alphagsm_env(config)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "AlphaGSM test", "")

    monkeypatch.setattr(helpers.subprocess, "run", run)
    helpers.run_alphagsm(env, "--version")
    assert calls[0][0] == [str(binary), "--version"]
    assert Path(calls[0][1]["cwd"]) == tmp_path
    assert "PYTHONPATH" not in env


def test_integration_source_default_is_preserved(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.delenv("ALPHAGSM_BINARY", raising=False)
    env = helpers.alphagsm_env(tmp_path / "alphagsm.conf")
    assert env["PYTHONPATH"] == str(helpers.REPO_ROOT / "src")
    assert helpers.alphagsm_command(env) == [sys.executable, str(helpers.ALPHAGSM_SCRIPT)]
