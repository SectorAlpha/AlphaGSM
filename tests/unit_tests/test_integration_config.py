"""Tests for shared integration-test config generation."""

import importlib
from pathlib import Path
import re

from tests.integration_tests.conftest import write_config


def test_default_runtime_backend_stays_process_outside_github_actions(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    assert helpers.default_runtime_backend() == "process"


def test_default_runtime_backend_uses_auto_on_github_actions(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    assert helpers.default_runtime_backend() == "auto"


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
