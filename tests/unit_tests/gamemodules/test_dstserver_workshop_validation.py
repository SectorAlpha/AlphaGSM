"""Validate disposable DST fixtures and strict native mod execution evidence."""

import importlib

import pytest


def helper():
    """Load the shared smoke/integration harness."""
    return importlib.import_module("tests.smoke_tests.dst_workshop")


def test_cluster_staging_copies_config_only_and_keeps_token_private(tmp_path, capsys):
    source = tmp_path / "source"
    (source / "Master").mkdir(parents=True)
    (source / "cluster.ini").write_text('[NETWORK]\ncluster_name=Original\n[SHARD]\nshard_enabled=true\n')
    (source / "cluster_token.txt").write_text("fixture-private-token")
    (source / "Master" / "server.ini").write_text('[NETWORK]\nserver_port=10999\n')
    (source / "Master" / "server_log.txt").write_text("stale engine evidence")
    (source / "Master" / "save").mkdir()
    (source / "Master" / "save" / "world").write_text("operator world")
    (source / "Master" / "modoverrides.lua").write_text("operator mods")
    destination = tmp_path / "disposable"
    helper().stage_cluster(source, destination, 18000, 18001, 18002)
    assert (destination / "cluster_token.txt").read_text() == "fixture-private-token"
    assert (destination / "cluster_token.txt").stat().st_mode & 0o777 == 0o600
    assert not (destination / "Master" / "save").exists()
    assert not (destination / "Master" / "server_log.txt").exists()
    assert not (destination / "Master" / "modoverrides.lua").exists()
    assert "18001" in (destination / "Master" / "server.ini").read_text()
    assert "Original" in (source / "cluster.ini").read_text()
    assert "fixture-private-token" not in capsys.readouterr().out


def test_cluster_staging_rejects_symlinked_credentials(tmp_path):
    source = tmp_path / "source"
    (source / "Master").mkdir(parents=True)
    (source / "cluster.ini").write_text("[NETWORK]\n")
    (source / "Master" / "server.ini").write_text("[NETWORK]\n")
    token = tmp_path / "token"
    token.write_text("private")
    (source / "cluster_token.txt").symlink_to(token)
    with pytest.raises(ValueError, match="regular"):
        helper().stage_cluster(source, tmp_path / "destination", 18000, 18001, 18002)


def test_native_evidence_requires_modmain_execution_and_success():
    text = ('[00:00:10]: Loading mod: workshop-378160973 (Global Positions) Version:1\n'
            '[00:00:11]: Mod: workshop-378160973 (Global Positions) Loading modmain.lua\n'
            '[00:00:12]: LOADING LUA SUCCESS\n')
    helper().assert_workshop_loaded(text)


@pytest.mark.parametrize("text", [
    'Downloaded workshop-378160973\nLOADING LUA SUCCESS\n',
    'Mod: workshop-378160973 (Global Positions) Mod had no modmain.lua. Skipping.\nLOADING LUA SUCCESS\n',
    'Mod: workshop-378160973 (Global Positions) Loading modmain.lua\nLUA ERROR\n',
    'Mod: workshop-111 (Other mod) Loading modmain.lua\nLOADING LUA SUCCESS\n',
    'LOADING LUA SUCCESS\nMod: workshop-378160973 (Global Positions) Loading modmain.lua\n',
    'Mod: workshop-378160973 (Global Positions) Loading modmain.lua\nError loading mod\nLOADING LUA SUCCESS\n',
])
def test_native_evidence_rejects_download_only_or_failed_load(text):
    with pytest.raises(AssertionError):
        helper().assert_workshop_loaded(text)
