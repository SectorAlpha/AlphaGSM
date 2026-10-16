"""Tests for shared integration-test config generation."""

import ast
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from tests.integration_tests.conftest import write_config


def test_default_runtime_backend_stays_process_outside_github_actions(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    assert helpers.default_runtime_backend() == "process"


def test_default_runtime_backend_uses_auto_on_github_actions(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    assert helpers.default_runtime_backend() == "auto"


@pytest.mark.parametrize("selected,expected", [
    (None, ("process", "docker")),
    ("process", ("process",)),
    ("docker", ("docker",)),
])
def test_workshop_runtime_backends_collect_only_selected_lane(monkeypatch, selected, expected):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    if selected is None:
        monkeypatch.delenv("ALPHAGSM_TEST_RUNTIME_BACKEND", raising=False)
    else:
        monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", selected)
    assert helpers.workshop_runtime_backends() == expected


@pytest.mark.parametrize("selected", ["", "auto", "PROCESS", " docker", "podman", "process,docker"])
def test_workshop_runtime_backends_reject_ambiguous_or_invalid_lane(monkeypatch, selected):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", selected)
    with pytest.raises(ValueError, match="ALPHAGSM_TEST_RUNTIME_BACKEND"):
        helpers.workshop_runtime_backends()


@pytest.mark.parametrize("filename", [
    "test_ark.py", "test_asrdserver.py", "test_avserver.py", "test_bb2server.py",
    "test_btserver.py", "test_conanexiles.py", "test_doiserver.py", "test_gmodserver.py",
    "test_insserver.py", "test_l4d2server.py", "test_nmrihserver.py", "test_ns2server.py",
    "test_projectzomboid.py", "test_seserver.py", "test_squadserver.py",
    "test_stationeersserver.py", "test_terraria_tmodloader.py", "test_tf2.py",
    "test_unturned.py", "test_wreckfestserver.py",
])
def test_anonymous_workshop_cases_use_shared_runtime_collection(filename):
    path = Path(__file__).resolve().parents[1] / "integration_tests" / filename
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cases = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name.startswith("test_")
             and ("workshop" in node.name or filename in {"test_conanexiles.py", "test_squadserver.py"})]
    assert cases, filename
    for case in cases:
        parameterizations = [node for node in case.decorator_list
                             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr == "parametrize"]
        assert any(len(node.args) >= 2 and isinstance(node.args[1], ast.Call)
                   and isinstance(node.args[1].func, ast.Name)
                   and node.args[1].func.id == "workshop_runtime_backends"
                   for node in parameterizations), f"{filename}:{case.name} bypasses selected CI lane"


def test_write_config_uses_home_download_paths_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("ALPHAGSM_WORK_DIR", raising=False)

    config_path = tmp_path / "alphagsm.conf"
    home_dir = tmp_path / "home"
    write_config(config_path, home_dir)

    text = config_path.read_text()
    assert f"db_path = {home_dir / 'downloads' / 'downloads.txt'}" in text
    assert f"target_path = {home_dir / 'downloads' / 'downloads'}" in text
    assert "[runtime]" in text
    assert "backend = process" in text
    assert "[process]" in text
    assert "[docker]" in text


def test_write_config_keeps_downloads_under_home_when_work_dir_is_set(tmp_path, monkeypatch):
    shared_root = tmp_path / "shared-download-root"
    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(shared_root))
    monkeypatch.delenv("ALPHAGSM_SHARE_DOWNLOAD_CACHE", raising=False)

    config_path = tmp_path / "alphagsm.conf"
    home_dir = tmp_path / "home"
    write_config(config_path, home_dir, session_tag="AlphaGSM-TF2-IT#")

    text = config_path.read_text()
    assert f"db_path = {home_dir / 'downloads' / 'downloads.txt'}" in text
    assert f"target_path = {home_dir / 'downloads' / 'downloads'}" in text
    assert "sessiontag = AlphaGSM-TF2-IT#" in text
    assert "[runtime]" in text
    assert "backend = process" in text
    assert "[process]" in text
    assert "[docker]" in text
    assert "[downloader.steamcmd]" in text
    assert f"steamcmd_path = {shared_root / 'steamcmd'}" in text


def test_write_config_uses_shared_download_root_when_opted_in(tmp_path, monkeypatch):
    shared_root = tmp_path / "shared-download-root"
    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(shared_root))
    monkeypatch.setenv("ALPHAGSM_SHARE_DOWNLOAD_CACHE", "1")

    config_path = tmp_path / "alphagsm.conf"
    home_dir = tmp_path / "home"
    write_config(config_path, home_dir, session_tag="AlphaGSM-TF2-IT#")

    text = config_path.read_text()
    assert f"db_path = {shared_root / 'downloads' / 'downloads.txt'}" in text
    assert f"target_path = {shared_root / 'downloads' / 'downloads'}" in text
    assert "sessiontag = AlphaGSM-TF2-IT#" in text
    assert "[runtime]" in text
    assert "backend = process" in text
    assert "[process]" in text
    assert "[docker]" in text
    assert "[downloader.steamcmd]" in text
    assert f"steamcmd_path = {shared_root / 'steamcmd'}" in text


def test_write_config_steamcmd_path_loads_in_fresh_process(tmp_path, monkeypatch):
    shared_root = tmp_path / "shared-download-root"
    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(shared_root))

    config_path = tmp_path / "alphagsm.conf"
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    write_config(config_path, home_dir)

    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; import utils.steamcmd as steamcmd; "
                "print(json.dumps([steamcmd.STEAMCMD_DIR, steamcmd.STEAMCMD_EXE]))"
            ),
        ],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    steamcmd_dir, steamcmd_exe = json.loads(result.stdout)
    assert steamcmd_dir == str(shared_root / "steamcmd")
    assert steamcmd_exe == str(shared_root / "steamcmd" / "steamcmd.sh")


def test_write_config_auto_prefers_docker_for_explicit_container_modules(
    tmp_path, monkeypatch
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setattr(
        helpers,
        "_module_uses_explicit_docker_runtime",
        lambda module_name, servermodulespackage="gamemodules.": True,
    )

    config_path = tmp_path / "alphagsm.conf"
    home_dir = tmp_path / "home"
    write_config(
        config_path,
        home_dir,
        runtime_backend="auto",
        backend="subprocess",
        module_name="terraria.tshock",
    )

    text = config_path.read_text()
    assert "[runtime]" in text
    assert "backend = docker" in text
    assert "[process]" in text
    assert "[docker]" in text


def test_write_config_auto_falls_back_to_process_for_non_container_modules(
    tmp_path, monkeypatch
):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setattr(
        helpers,
        "_module_uses_explicit_docker_runtime",
        lambda module_name, servermodulespackage="gamemodules.": False,
    )

    config_path = tmp_path / "alphagsm.conf"
    home_dir = tmp_path / "home"
    write_config(
        config_path,
        home_dir,
        runtime_backend="auto",
        module_name="identityserver",
    )

    text = config_path.read_text()
    assert "[runtime]" in text
    assert "backend = process" in text
    assert "[process]" in text
    assert "[docker]" in text


def test_integration_tests_branch_on_effective_runtime_backend():
    integration_root = Path(__file__).resolve().parents[1] / "integration_tests"
    forbidden_pattern = re.compile(
        r"\bruntime_backend\s*==\s*[\"'](?:docker|process)[\"']"
    )

    offenders = []
    for path in sorted(integration_root.glob("test_*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if forbidden_pattern.search(line):
                offenders.append(f"{path.relative_to(integration_root.parent)}:{lineno}")

    assert offenders == [], (
        "Integration tests must branch on effective_runtime_backend(...) "
        "rather than the raw ALPHAGSM_TEST_RUNTIME_BACKEND value: "
        + ", ".join(offenders)
    )


def test_integration_tests_do_not_pass_runtime_name_as_required_command():
    integration_root = Path(__file__).resolve().parents[1] / "integration_tests"
    offenders = []

    for path in sorted(integration_root.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "require_command_for_runtime":
                continue
            if isinstance(node.args[0], ast.Name) and node.args[0].id == "runtime_backend":
                offenders.append(
                    f"{path.relative_to(integration_root.parent)}:{node.lineno}"
                )

    assert offenders == [], (
        "Pass a command name first and runtime_backend as a keyword: "
        + ", ".join(offenders)
    )
