"""Tests for shared integration-test config generation."""

from pathlib import Path

from tests.integration_tests.conftest import write_config


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
