"""Offline file-requirement and acquisition-guidance contract tests."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from server import ServerError


ROOT = Path(__file__).resolve().parents[3]
NON_FILE_MODULES = {"astroneerserver", "lifeisfeudalserver", "qlserver"}
MODULES = [line.split("\t", 1)[0] for line in (ROOT / "enabled_byo_servers.conf").read_text().splitlines()
           if line.strip() and not line.startswith("#") and line.split("\t", 1)[0] not in NON_FILE_MODULES]


def helpers():
    from utils import byo_files
    return byo_files


def test_each_file_byo_module_declares_actionable_requirements(tmp_path):
    for module_id in MODULES:
        module = importlib.import_module("gamemodules." + module_id)
        assert callable(getattr(module, "get_asset_requirements", None)), module_id
        server = SimpleNamespace(name="example", data={"dir": str(tmp_path), "password": "must-not-escape"})
        recipe = module.get_asset_requirements(server)
        assert recipe["module"] == module_id
        assert recipe["requirements"] and recipe["sources"]
        assert isinstance(recipe["managed_import"], bool)
        assert all(source["instructions"] and source["kind"] for source in recipe["sources"])
        assert "must-not-escape" not in json.dumps(recipe)


def test_presence_checks_distinguish_files_globs_and_populated_directories(tmp_path):
    recipe = {"requirements": [
        {"path": "base/pak0.pk3", "kind": "file"},
        {"path": "zone/**/*.ff", "kind": "glob"},
        {"path": "content", "kind": "directory"},
    ], "sources": [{"id": "owned", "kind": "owned-install", "instructions": "Copy owned game data"}]}
    (tmp_path / "base").mkdir()
    (tmp_path / "base/pak0.pk3").write_bytes(b"pak")
    (tmp_path / "content").mkdir()
    report = helpers().inspect_files(tmp_path, recipe)
    assert report["missing"] == ["zone/**/*.ff", "content"]
    assert report["sources"] == recipe["sources"]
    assert report["game_readiness"] == "not-checked"
    (tmp_path / "zone/english").mkdir(parents=True)
    (tmp_path / "zone/english/mp.ff").write_bytes(b"zone")
    (tmp_path / "content/asset.dat").write_bytes(b"content")
    assert helpers().inspect_files(tmp_path, recipe)["ready"]


def test_alternatives_zero_bytes_and_directories_are_not_regular_files(tmp_path):
    recipe = {"requirements": [{"any_of": ["main/localized_*.iwd", "main/default.cfg"], "kind": "glob"}]}
    (tmp_path / "main").mkdir()
    (tmp_path / "main/localized_english.iwd").write_bytes(b"")
    (tmp_path / "main/default.cfg").mkdir()
    assert not helpers().inspect_files(tmp_path, recipe)["ready"]
    (tmp_path / "main/default.cfg").rmdir()
    (tmp_path / "main/default.cfg").write_bytes(b"config")
    assert helpers().inspect_files(tmp_path, recipe)["ready"]


def test_archive_map_requirement_checks_actual_member(tmp_path):
    recipe = {"requirements": [{"path": "main/*.pk3", "kind": "archive-member", "member": "maps/mp/mp_test.bsp"}]}
    (tmp_path / "main").mkdir()
    path = tmp_path / "main/maps.pk3"
    path.write_bytes(b"not an archive")
    assert not helpers().inspect_files(tmp_path, recipe)["ready"]
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("maps/mp/mp_test.bsp", b"map")
    assert helpers().inspect_files(tmp_path, recipe)["ready"]


def test_links_cannot_satisfy_required_files(tmp_path):
    outside = tmp_path / "outside"
    outside.write_bytes(b"owned")
    root = tmp_path / "server"
    root.mkdir()
    (root / "pak0.pk3").symlink_to(outside)
    assert not helpers().inspect_files(root, {"requirements": [{"path": "pak0.pk3", "kind": "file"}]})["ready"]


@pytest.mark.parametrize("path", ["../escape", "/absolute", "C:/drive", "a\\b", "a/../../b"])
def test_unsafe_declared_paths_are_rejected(tmp_path, path):
    with pytest.raises(ServerError, match="path"):
        helpers().inspect_files(tmp_path, {"requirements": [{"path": path, "kind": "file"}]})


def test_ets2_uses_configured_home_and_rejects_empty_exports(tmp_path):
    from gamemodules import ets2server
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path), "configdir": "custom-home"})
    recipe = ets2server.get_asset_requirements(server)
    assert {r["path"] for r in recipe["requirements"]} == {
        "custom-home/server_packages.sii", "custom-home/server_packages.dat"}
    home = tmp_path / "custom-home"
    home.mkdir()
    for filename in ("server_packages.sii", "server_packages.dat"):
        (home / filename).write_bytes(b"")
    assert not helpers().inspect_files(tmp_path, recipe)["ready"]
    for path in home.iterdir():
        path.write_bytes(b"export")
    assert helpers().inspect_files(tmp_path, recipe)["ready"]


def test_dst_uses_instance_cluster_and_shard_without_exposing_token(tmp_path):
    from gamemodules import dstserver
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path), "confdir": "cfg", "cluster": "world", "shard": "Caves", "token": "private-token"})
    recipe = dstserver.get_asset_requirements(server)
    assert {r["path"] for r in recipe["requirements"]} == {
        "cfg/world/cluster_token.txt", "cfg/world/cluster.ini", "cfg/world/Caves/server.ini"}
    assert not recipe["managed_import"]
    assert "private-token" not in json.dumps(recipe)


def test_steam_sources_use_base_game_not_dedicated_app(tmp_path):
    from gamemodules import coduoserver, q3server
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path)})
    for module, app_id in ((coduoserver, 2620), (q3server, 2200)):
        source = next(s for s in module.get_asset_requirements(server)["sources"] if s["kind"] == "steamcmd")
        assert source["app_id"] == app_id
        assert source["platform"] == "windows"
        assert source["authentication"] == "required"
        assert source["live_validated"] is False
