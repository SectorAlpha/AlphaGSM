"""GMod Workshop activation and engine evidence regressions."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from gamemodules import gmodserver
from server import ServerError
from server.modsupport import workshop
from server.modsupport.errors import ModSupportError


@pytest.fixture
def server(tmp_path):
    instance = SimpleNamespace(name="gmodworkshop", data={})
    gmodserver.configure(instance, ask=False, port=27015, dir=str(tmp_path / "server"))
    return instance


@pytest.fixture
def metadata(monkeypatch):
    def details(ids):
        return [{"publishedfileid": str(item), "result": 1, "consumer_app_id": 4000,
                 "file_type": 2 if str(item) == "900" else 0} for item in ids]

    def collections(ids):
        return [{"publishedfileid": str(item), "result": 1, "children": [
            {"publishedfileid": "123", "filetype": 0},
            {"publishedfileid": "124", "filetype": 0}]} for item in ids]

    def responses(method, ids, key):
        del key
        records = details(ids) if method == "GetPublishedFileDetails" else collections(ids)
        return {entry["publishedfileid"]: entry for entry in records}

    monkeypatch.setattr(workshop, "_post_details", responses)


def add(server, source="workshop", identifier="123"):
    gmodserver.command_functions["mod"](server, "add", source, identifier)


def test_ids_urls_and_collections_share_workshop_desired_state(server, metadata):
    del metadata
    add(server, identifier="https://steamcommunity.com/sharedfiles/filedetails/?id=123")
    add(server, "workshop-collection", "900")
    assert [entry["workshop_id"] for entry in server.data["mods"]["desired"]["workshop"]] == ["123", "124"]
    assert gmodserver.workshop_app_id == 4000
    assert gmodserver.steam_app_id == 4020


def test_wrong_game_item_is_rejected_before_desired_state_changes(server, monkeypatch):
    monkeypatch.setattr(workshop, "_post_details", lambda method, ids, key: {str(item): {"publishedfileid": str(item), "result": 1, "consumer_app_id": 550, "file_type": 0} for item in ids})
    with pytest.raises(ServerError, match="4000"):
        add(server)
    assert server.data["mods"]["desired"]["workshop"] == []


def test_apply_and_cleanup_flat_gma_keep_operator_addon(server, metadata, monkeypatch, tmp_path):
    del metadata
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "addon.gma").write_bytes(_gma_bytes([("lua/autorun/fixture.lua", b"print(123)")]))
    calls = []

    def download(path, app_id, item_id, anonymous):
        calls.append((app_id, item_id, anonymous))
        return payload

    monkeypatch.setattr(gmodserver.steamcmd, "download_workshop_item", download)
    add(server)
    addons = Path(server.data["dir"]) / "garrysmod" / "addons"
    addons.mkdir(parents=True)
    operator = addons / "operator.gma"
    operator.write_bytes(b"operator")
    gmodserver.command_functions["mod"](server, "apply")
    installed = addons / "123" / "lua" / "autorun" / "fixture.lua"
    assert installed.read_bytes() == b"print(123)"
    assert calls == [(4000, "123", True)]
    assert server.data["mods"]["installed"][0]["installed_files"] == ["garrysmod/addons/123/lua/autorun/fixture.lua"]
    gmodserver.command_functions["mod"](server, "cleanup")
    assert not installed.exists()
    assert operator.read_bytes() == b"operator"


@pytest.mark.parametrize("content", [b"not a gma", b"GMAD\xff", b"GMAD", b"GMAD\x00"])
def test_download_rejects_invalid_gma_before_staging(tmp_path, monkeypatch, content):
    (tmp_path / "addon.gma").write_bytes(content)
    monkeypatch.setattr(gmodserver.steamcmd, "download_workshop_item", lambda *args: tmp_path)
    with pytest.raises(ModSupportError, match="GMA"):
        gmodserver.download_workshop_addon(tmp_path / "cache", 4000, "123", True)


def test_download_rejects_symlink_payload(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.write_bytes(b"GMAD\x03" + b"\0" * 40)
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "addon.gma").symlink_to(outside)
    monkeypatch.setattr(gmodserver.steamcmd, "download_workshop_item", lambda *args: payload)
    with pytest.raises(ModSupportError, match="GMA"):
        gmodserver.download_workshop_addon(tmp_path / "cache", 4000, "123", True)


def test_prestart_runs_autoapply_after_valve_preparation(server, monkeypatch):
    calls = []
    monkeypatch.setattr(gmodserver.MODULE, "prestart", lambda *args, **kwargs: calls.append("valve"))
    monkeypatch.setattr(gmodserver.MOD_SUPPORT, "apply_configured_mods", lambda *args: calls.append("mods"))
    gmodserver.prestart(server)
    assert calls == ["valve", "mods"]
    server.data["mods"]["autoapply"] = False
    calls.clear()
    gmodserver.prestart(server)
    assert calls == ["valve"]


def test_docker_spec_preserves_interactive_engine_console(server, monkeypatch):
    monkeypatch.setattr(gmodserver.runtime_module, "build_container_spec", lambda instance, **kwargs: kwargs)
    spec = gmodserver.get_container_spec(server)
    assert spec["stdin_open"] is True
    assert spec["tty"] is True


def test_launch_explicitly_enables_engine_console(server, monkeypatch):
    monkeypatch.setattr(gmodserver.MODULE, "get_start_command", lambda instance: (["./srcds_run", "-game", "garrysmod"], "/srv/server"))
    command, directory = gmodserver.get_start_command(server)
    assert command == ["./srcds_run", "-game", "garrysmod", "-console"]
    assert directory == "/srv/server"


def test_container_source_console_receives_fifo_input_through_real_pty(server, monkeypatch):
    import subprocess
    import sys
    monkeypatch.setattr(gmodserver.MODULE, "get_start_command", lambda instance: ([
        sys.executable, "-c", 'import sys; print("ENGINE_TTY=" + str(sys.stdin.isatty())); print("ENGINE_INPUT=" + input())'], "/tmp"))
    command, directory = gmodserver._get_container_start_command(server)
    result = subprocess.run(command, cwd=directory, input="probe-marker\n", text=True,
                            capture_output=True, timeout=10, check=True)
    assert "ENGINE_TTY=True" in result.stdout
    assert "ENGINE_INPUT=probe-marker" in result.stdout


def test_probe_requires_fresh_engine_mount_and_rejects_unmounted_or_echoed_text():
    helper_path = Path(__file__).parents[2] / "smoke_tests" / "gmod_workshop.py"
    spec = importlib.util.spec_from_file_location("gmod_workshop_probe", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    good = '{"workshop_id":"123","mounted":true}'
    helper.assert_workshop_mounts("old evidence\nBEGIN-fresh\n" + good + "\nEND-fresh", ["123"], "fresh")
    for text in [good, 'lua_run print("BEGIN-fresh")\n' + good + '\nEND-fresh',
                 'BEGIN-fresh\n{"workshop_id":"123","mounted":false}\nEND-fresh',
                 'BEGIN-fresh\n{"workshop_id":"other123","mounted":true}\nEND-fresh']:
        with pytest.raises(AssertionError):
            helper.assert_workshop_mounts(text, ["123"], "fresh")


@pytest.mark.parametrize("item_id,api", [("557962238", "ulib_loaded"), ("557962280", "ulx_loaded")])
def test_probe_requires_admin_addon_api_execution(item_id, api):
    helper_path = Path(__file__).parents[2] / "smoke_tests" / "gmod_workshop.py"
    spec = importlib.util.spec_from_file_location("gmod_workshop_api_probe", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    for value in ("false", "null"):
        log = f'BEGIN-fresh\n{{"workshop_id":"{item_id}","mounted":true,"{api}":{value}}}\nEND-fresh'
        with pytest.raises(AssertionError):
            helper.assert_workshop_mounts(log, [item_id], "fresh")
    log = f'\x1b[0mBEGIN-fresh\n{{"workshop_id":"{item_id}","mounted":true,"{api}":true}}\nEND-fresh\x1b[0m'
    helper.assert_workshop_mounts(log, [item_id], "fresh")


def test_collection_wrong_game_child_is_atomic(server, monkeypatch):
    def details(method, ids, key):
        del key
        if method == "GetCollectionDetails":
            return {"900": {"children": [{"publishedfileid": "123"}, {"publishedfileid": "124"}]}}
        return {str(item): {"consumer_app_id": 550 if item == "124" else 4000,
                           "file_type": 2 if item == "900" else 0} for item in ids}

    monkeypatch.setattr(workshop, "_post_details", details)
    with pytest.raises(ServerError, match="4000"):
        add(server, "workshop-collection", "900")
    assert server.data["mods"]["desired"]["workshop"] == []


def test_apply_rejects_symlink_addon_directory_without_writing_outside(server, metadata, monkeypatch, tmp_path):
    del metadata
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "addon.gma").write_bytes(_gma_bytes([("lua/autorun/fixture.lua", b"print(123)")]))
    monkeypatch.setattr(gmodserver.steamcmd, "download_workshop_item", lambda *args: payload)
    outside = tmp_path / "operator"
    outside.mkdir()
    game_root = Path(server.data["dir"]) / "garrysmod"
    game_root.mkdir(parents=True)
    (game_root / "addons").symlink_to(outside, target_is_directory=True)
    add(server)
    with pytest.raises(ServerError, match="symlink|outside"):
        gmodserver.command_functions["mod"](server, "apply")
    assert list(outside.iterdir()) == []


def test_cleanup_rejects_traversal_and_preserves_operator_file(server, tmp_path):
    outside = tmp_path / "operator.gma"
    outside.write_bytes(b"operator")
    server.data["mods"]["installed"] = [{
        "source_type": "workshop", "resolved_id": "workshop.123",
        "installed_files": ["../operator.gma"],
    }]
    with pytest.raises(ServerError, match="unsafe"):
        gmodserver.command_functions["mod"](server, "cleanup")
    assert outside.read_bytes() == b"operator"


def _gma_bytes(entries):
    import struct
    import zlib
    header = b"GMAD\x03" + b"\0" * 16 + b"\0fixture\0{}\0author\0" + struct.pack("<I", 1)
    for index, (name, data) in enumerate(entries, 1):
        header += struct.pack("<I", index) + name.encode() + b"\0" + struct.pack("<qI", len(data), zlib.crc32(data))
    payload = header + b"\0" * 4 + b"".join(data for _, data in entries)
    return payload + struct.pack("<I", zlib.crc32(payload))


@pytest.mark.parametrize("entries", [
    [("../escape.lua", b"unsafe")], [("/abs.lua", b"unsafe")],
    [("lua/a.lua", b"one"), ("lua/a.lua", b"two")],
    [("lua/a.lua", b"one"), ("lua/a.lua/child", b"two")],
])
def test_gma_extraction_rejects_unsafe_paths_without_writes(tmp_path, entries):
    from gamemodules.gmodserver.gma import extract_gma
    archive = tmp_path / "addon.gma"
    archive.write_bytes(_gma_bytes(entries))
    stage = tmp_path / "stage"
    with pytest.raises(ModSupportError):
        extract_gma(archive, stage)
    assert not stage.exists()


def test_gma_extraction_rejects_corrupt_crc_and_truncation(tmp_path):
    from gamemodules.gmodserver.gma import extract_gma
    data = _gma_bytes([("lua/autorun/fixture.lua", b"print('test')")])
    archive = tmp_path / "addon.gma"
    for broken in (data[:-1], data[:-5] + b"x" + data[-4:]):
        archive.write_bytes(broken)
        with pytest.raises(ModSupportError):
            extract_gma(archive, tmp_path / "stage")
        assert not (tmp_path / "stage").exists()


def test_gma_extraction_checks_file_crc_even_with_valid_archive_crc(tmp_path):
    import struct
    import zlib
    from gamemodules.gmodserver.gma import extract_gma
    data = bytearray(_gma_bytes([("lua/fixture.lua", b"test payload")]))
    payload_start = len(data) - 4 - len(b"test payload")
    data[payload_start - 8:payload_start - 4] = struct.pack("<I", 123)
    data[-4:] = struct.pack("<I", zlib.crc32(data[:-4]))
    archive = tmp_path / "addon.gma"
    archive.write_bytes(data)
    with pytest.raises(ModSupportError, match="file CRC"):
        extract_gma(archive, tmp_path / "stage")
    assert not (tmp_path / "stage").exists()


def test_gma_extraction_bounds_file_count_before_writing(tmp_path, monkeypatch):
    from gamemodules.gmodserver import gma
    monkeypatch.setattr(gma, "MAX_GMA_FILES", 1)
    archive = tmp_path / "addon.gma"
    archive.write_bytes(_gma_bytes([("lua/a.lua", b"a"), ("lua/b.lua", b"b")]))
    with pytest.raises(ModSupportError, match="file count"):
        gma.extract_gma(archive, tmp_path / "stage")
    assert not (tmp_path / "stage").exists()


def test_gma_collision_is_rejected_before_any_payload_copy(server, metadata, monkeypatch, tmp_path):
    del metadata
    payload = tmp_path / "download"
    payload.mkdir()
    (payload / "addon.gma").write_bytes(_gma_bytes([
        ("lua/autorun/a_new.lua", b"New payload"),
        ("lua/autorun/z_operator.lua", b"Replacement payload"),
    ]))
    monkeypatch.setattr(gmodserver.steamcmd, "download_workshop_item", lambda *args: payload)
    add(server)
    addon = Path(server.data["dir"]) / "garrysmod/addons/123/lua/autorun"
    addon.mkdir(parents=True)
    operator = addon / "z_operator.lua"
    operator.write_bytes(b"Operator payload")
    with pytest.raises(ServerError, match="collision|unowned"):
        gmodserver.MOD_SUPPORT.apply_configured_mods(server)
    assert operator.read_bytes() == b"Operator payload"
    assert not (addon / "a_new.lua").exists()
    assert server.data["mods"]["installed"] == []
