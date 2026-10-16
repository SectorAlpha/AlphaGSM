"""Offline file-requirement and acquisition-guidance contract tests."""

import importlib
import json
import stat
from pathlib import Path
from types import SimpleNamespace
import sys
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


@pytest.mark.skipif(sys.platform != "linux", reason="Linux path case semantics")
def test_q3_installed_inspection_rejects_source_casing(tmp_path):
    from gamemodules import q3server
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path)})
    recipe = q3server.get_asset_requirements(server)
    (tmp_path / "BaseQ3").mkdir()
    (tmp_path / "BaseQ3/PAK0.PK3").write_bytes(b"owned-data")

    report = helpers().inspect_files(tmp_path, recipe)

    assert not report["ready"]
    assert report["missing"] == ["baseq3/pak0.pk3"]


@pytest.mark.parametrize("insensitive,ready", [(False, False), (True, True)])
@pytest.mark.skipif(sys.platform != "linux", reason="Linux path case semantics")
def test_source_inspection_honors_recipe_case_policy(tmp_path, insensitive, ready):
    recipe = {"case_insensitive": insensitive,
              "requirements": [{"path": "baseq3/pak0.pk3", "kind": "file"}]}
    (tmp_path / "BaseQ3").mkdir()
    (tmp_path / "BaseQ3/PAK0.PK3").write_bytes(b"owned-data")

    assert helpers().inspect_files(tmp_path, recipe, source=True)["ready"] is ready


@pytest.mark.skipif(sys.platform != "linux", reason="Linux path case semantics")
def test_staged_inspection_requires_canonical_paths(tmp_path):
    recipe = {"case_insensitive": True,
              "requirements": [{"path": "baseq3/pak0.pk3", "kind": "file"}]}
    (tmp_path / "BaseQ3").mkdir()
    (tmp_path / "BaseQ3/PAK0.PK3").write_bytes(b"owned-data")

    with pytest.raises(ServerError, match="Selected content lacks required files: baseq3/pak0.pk3"):
        helpers().validate_staged_files(tmp_path, recipe, "")


def test_q3_import_normalizes_source_before_installed_inspection(tmp_path):
    from gamemodules import q3server
    from utils import asset_import
    source = tmp_path / "owned"
    target = tmp_path / "server"
    server = SimpleNamespace(name="test", data={"dir": str(target)})
    recipe = q3server.get_asset_requirements(server)
    (source / "BaseQ3").mkdir(parents=True)
    (source / "BaseQ3/PAK0.PK3").write_bytes(b"owned-data")

    report = asset_import.import_assets(source, target, recipe)

    assert report["copied"] == ["baseq3/pak0.pk3"]
    assert (target / "baseq3/pak0.pk3").read_bytes() == b"owned-data"
    assert helpers().inspect_files(target, recipe)["ready"]
    q3server._assert_required_base_assets(str(target))


@pytest.mark.parametrize("member_case_insensitive,ready", [(False, False), (True, True)])
@pytest.mark.parametrize("source", [False, True])
@pytest.mark.parametrize("filesystem_insensitive", [False, True])
@pytest.mark.parametrize("uppercase_pattern", [False, True])
def test_archive_member_case_policy_is_independent(
        tmp_path, member_case_insensitive, ready, source, filesystem_insensitive, uppercase_pattern):
    patterns = ["maps/mp/mp_test.bsp", "maps/mp/mp_test.d3dbsp"]
    if uppercase_pattern:
        patterns = [pattern.upper() for pattern in patterns]
    recipe = {"case_insensitive": filesystem_insensitive, "requirements": [{
        "path": "maps.pk3", "kind": "archive-member",
        "member_any_of": patterns,
        "member_case_insensitive": member_case_insensitive,
    }]}
    member = "maps/mp/mp_test.d3dbsp" if uppercase_pattern else "MAPS/MP/MP_TEST.D3DBSP"
    with zipfile.ZipFile(tmp_path / "maps.pk3", "w") as bundle:
        bundle.writestr(member, b"map")

    assert helpers().inspect_files(tmp_path, recipe, source=source)["ready"] is ready


@pytest.mark.parametrize("member", ["././maps/mp/mp_test.bsp", "maps\\mp\\mp_test.bsp"])
def test_legacy_archive_member_normalizes_member_names(tmp_path, member):
    recipe = {"requirements": [{"path": "maps.pk3", "kind": "archive-member",
                                "member": "maps/mp/mp_test.bsp"}]}
    with zipfile.ZipFile(tmp_path / "maps.pk3", "w") as bundle:
        bundle.writestr(member, b"map")

    assert helpers().inspect_files(tmp_path, recipe)["ready"]


@pytest.mark.parametrize("alternatives", [[], "maps/mp/map.bsp", None, (),
    ["maps/mp/map.bsp", "../escape"], ["maps/mp/map.bsp", "maps\\mp\\map.bsp"]])
def test_archive_member_alternatives_are_validated_before_access(tmp_path, monkeypatch, alternatives):
    def unexpected_access(*_args, **_kwargs):
        pytest.fail("Archive paths accessed before validating all member alternatives")
    monkeypatch.setattr(helpers(), "_matches", unexpected_access)
    recipe = {"requirements": [{"path": "maps.pk3", "kind": "archive-member",
                                "member": "maps/mp/map.bsp", "member_any_of": alternatives}]}

    with pytest.raises(ServerError, match="path|alternatives"):
        helpers().inspect_files(tmp_path, recipe)


@pytest.mark.parametrize("mode,payload", [
    (stat.S_IFREG | 0o644, b""),
    (stat.S_IFDIR | 0o755, b"map"),
    (stat.S_IFLNK | 0o777, b"maps/mp/other.bsp"),
    (stat.S_IFIFO | 0o644, b"map"),
])
def test_archive_member_requires_nonempty_regular_file(tmp_path, mode, payload):
    recipe = {"requirements": [{"path": "maps.pk3", "kind": "archive-member",
                                "member": "maps/mp/mp_test.bsp"}]}
    member = zipfile.ZipInfo("maps/mp/mp_test.bsp")
    member.create_system = 3
    member.external_attr = mode << 16
    with zipfile.ZipFile(tmp_path / "maps.pk3", "w") as bundle:
        bundle.writestr(member, payload)

    assert not helpers().inspect_files(tmp_path, recipe)["ready"]


def test_staged_archive_members_are_not_translated_by_import_target(tmp_path):
    recipe = {"requirements": [{"path": "main/maps.pk3", "kind": "archive-member",
                                "member_any_of": ["maps/mp/mp_test.bsp", "maps/mp/mp_test.d3dbsp"]}]}
    with zipfile.ZipFile(tmp_path / "maps.pk3", "w") as bundle:
        bundle.writestr("maps/mp/mp_test.d3dbsp", b"map")

    helpers().validate_staged_files(tmp_path, recipe, "main")


@pytest.mark.parametrize('setting', ['configdir', 'confdir'])
def test_absolute_config_home_translates_path_alternatives(tmp_path, setting):
    home = tmp_path / 'external-home'
    recipe = {'config_home_setting': setting, 'defaults': {setting: 'default-home'},
              'target': '{' + setting + '}', 'managed_import': True,
              'requirements': [{'any_of': ['{' + setting + '}/first.dat',
                                            '{' + setting + '}/second.dat'], 'kind': 'file'}]}
    (tmp_path / 'byo_assets.json').write_text(json.dumps(recipe))
    server = SimpleNamespace(name='test', data={'dir': str(tmp_path / 'server'), setting: str(home)})

    result = helpers().load_requirements(server, str(tmp_path / 'main.py'))

    assert result['requirements'][0]['any_of'] == ['first.dat', 'second.dat']
    assert result['managed_import'] is False
    assert helpers().inspection_root(server, result) == str(home)


@pytest.mark.parametrize('setting', ['dir', 'password', ''])
def test_config_home_opt_in_only_accepts_config_settings(tmp_path, setting):
    recipe = {'config_home_setting': setting, 'requirements': [{'path': 'file.dat'}]}
    (tmp_path / 'byo_assets.json').write_text(json.dumps(recipe))
    server = SimpleNamespace(name='test', data={'dir': str(tmp_path)})

    with pytest.raises(ServerError, match='configuration home setting'):
        helpers().load_requirements(server, str(tmp_path / 'main.py'))


@pytest.mark.parametrize('requirement', [
    {'path': 'outside.dat'},
    {'any_of': ['{configdir}/inside.dat', 'outside.dat']},
    {'path': '{configdir}/../escape.dat'},
    {'any_of': ['{configdir}/inside.dat', '{configdir}/../escape.dat']},
])
def test_absolute_config_home_keeps_requirement_paths_contained(tmp_path, requirement):
    recipe = {'config_home_setting': 'configdir', 'requirements': [requirement]}
    (tmp_path / 'byo_assets.json').write_text(json.dumps(recipe))
    server = SimpleNamespace(name='test', data={'dir': str(tmp_path / 'server'),
                                              'configdir': str(tmp_path / 'external-home')})

    with pytest.raises(ServerError, match='path|configuration home'):
        helpers().load_requirements(server, str(tmp_path / 'main.py'))
