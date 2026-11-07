"""Full coverage tests for qwserver."""

import os
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.qwserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.github_releases': MagicMock()}):
    import gamemodules.qwserver as mod
    from server import ServerError

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27500, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip", version="1.0")
    assert server.data['port'] == 27500

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27500
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["hostname"] = "test"
    server.data["startmap"] = "test"
    server.data["version"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27501", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "mvdsv"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    with patch.object(mod, '_install_base_content'):
        mod.install(server)


def test_install_base_content_downloads_shareware_and_maps(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"

    def fake_extract(archive_path, stage_root):
        archive_name = Path(archive_path).name
        stage_root = Path(stage_root)
        if archive_name == mod.QW_SERVER_BIN_NAME:
            ktx_root = stage_root / "ktx"
            ktx_root.mkdir(parents=True, exist_ok=True)
            (ktx_root / "qwprogs.so").write_text("plugin", encoding="utf-8")
            return
        if archive_name == mod.QW_SERVER_GPL_NAME:
            id1_root = stage_root / "id1" / "maps"
            id1_root.mkdir(parents=True, exist_ok=True)
            (id1_root / "b_exbox2.bsp").write_text("map", encoding="utf-8")
            maps_root = stage_root / "qw" / "maps"
            maps_root.mkdir(parents=True, exist_ok=True)
            (maps_root / "dm2.bsp").write_text("map", encoding="utf-8")
            return
        if archive_name == mod.QW_SERVER_NON_GPL_NAME:
            ktx_root = stage_root / "ktx" / "sound"
            ktx_root.mkdir(parents=True, exist_ok=True)
            (ktx_root / "flagcap.wav").write_text("sound", encoding="utf-8")
            return
        if archive_name == mod.QW_SERVER_CONFIGS_NAME:
            ktx_root = stage_root / "ktx"
            ktx_root.mkdir(parents=True, exist_ok=True)
            (ktx_root / "server.cfg").write_text("config", encoding="utf-8")
            return
        if archive_name == mod.QW_SHAREWARE_NAME:
            pak_root = stage_root / "ID1"
            pak_root.mkdir(parents=True, exist_ok=True)
            (pak_root / "PAK0.PAK").write_text("shareware", encoding="utf-8")
            return
        maps_root = stage_root / "qw" / "maps"
        maps_root.mkdir(parents=True, exist_ok=True)
        (maps_root / "mvdsv-kg.bsp").write_text("map", encoding="utf-8")

    with patch.object(mod, 'download_to_cache') as download_to_cache, \
         patch.object(mod, 'extract_zip_safe', side_effect=fake_extract):
        installed_base_content = mod._install_base_content(server)

    assert installed_base_content is True
    assert download_to_cache.call_count == 6
    download_to_cache.assert_any_call(
        mod.QW_SERVER_BIN_URL,
        allowed_hosts=("github.com",),
        target_path=Path(server.data["dir"]) / ".alphagsm" / "mods" / mod.QW_MOD_CACHE_DIRNAME / "bootstrap" / mod.QW_SERVER_BIN_NAME,
    )
    download_to_cache.assert_any_call(
        mod.QW_SERVER_GPL_URL,
        allowed_hosts=("github.com",),
        target_path=Path(server.data["dir"]) / ".alphagsm" / "mods" / mod.QW_MOD_CACHE_DIRNAME / "bootstrap" / mod.QW_SERVER_GPL_NAME,
    )
    download_to_cache.assert_any_call(
        mod.QW_SERVER_NON_GPL_URL,
        allowed_hosts=("github.com",),
        target_path=Path(server.data["dir"]) / ".alphagsm" / "mods" / mod.QW_MOD_CACHE_DIRNAME / "bootstrap" / mod.QW_SERVER_NON_GPL_NAME,
    )
    download_to_cache.assert_any_call(
        mod.QW_SERVER_CONFIGS_URL,
        allowed_hosts=("github.com",),
        target_path=Path(server.data["dir"]) / ".alphagsm" / "mods" / mod.QW_MOD_CACHE_DIRNAME / "bootstrap" / mod.QW_SERVER_CONFIGS_NAME,
    )
    download_to_cache.assert_any_call(
        mod.QW_SHAREWARE_URL,
        allowed_hosts=("github.com",),
        target_path=Path(server.data["dir"]) / ".alphagsm" / "mods" / mod.QW_MOD_CACHE_DIRNAME / "bootstrap" / mod.QW_SHAREWARE_NAME,
    )
    download_to_cache.assert_any_call(
        mod.QW_SERVER_MAPS_URL,
        allowed_hosts=("github.com",),
        target_path=Path(server.data["dir"]) / ".alphagsm" / "mods" / mod.QW_MOD_CACHE_DIRNAME / "bootstrap" / mod.QW_SERVER_MAPS_NAME,
    )
    assert (tmp_path / "id1" / "pak0.pak").read_text(encoding="utf-8") == "shareware"
    assert (tmp_path / "qw" / "maps" / "mvdsv-kg.bsp").read_text(encoding="utf-8") == "map"
    assert (tmp_path / "qw" / "maps" / "dm2.bsp").read_text(encoding="utf-8") == "map"
    assert (tmp_path / "ktx" / "server.cfg").read_text(encoding="utf-8") == "config"
    assert (tmp_path / "ktx" / "qwprogs.so").read_text(encoding="utf-8") == "plugin"


def test_install_base_content_skips_when_shareware_and_maps_exist(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    pak0_path = tmp_path / "id1" / "pak0.pak"
    dm2_path = tmp_path / "qw" / "maps" / "dm2.bsp"
    map_path = tmp_path / "qw" / "maps" / "mvdsv-kg.bsp"
    server_cfg_path = tmp_path / "ktx" / "server.cfg"
    qwprogs_path = tmp_path / "ktx" / "qwprogs.so"
    pak0_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    server_cfg_path.parent.mkdir(parents=True, exist_ok=True)
    pak0_path.write_text("existing", encoding="utf-8")
    dm2_path.write_text("existing", encoding="utf-8")
    map_path.write_text("existing", encoding="utf-8")
    server_cfg_path.write_text("existing", encoding="utf-8")
    qwprogs_path.write_text("existing", encoding="utf-8")

    with patch.object(mod, 'download_to_cache') as download_to_cache:
        installed_base_content = mod._install_base_content(server)

    assert installed_base_content is False
    download_to_cache.assert_not_called()

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "mvdsv"
    (tmp_path / "mvdsv").write_text("")
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./mvdsv",
        "-mem",
        "64",
        "-game",
        "ktx",
        "-port",
        "27015",
        "+hostname",
        "test",
        "+map",
        "test",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_quakeworld_launch_tokens():
    assert mod.setting_schema["port"].launch_arg_tokens == ("-port",)
    assert mod.setting_schema["hostname"].launch_arg_tokens == ("+hostname",)
    assert mod.setting_schema["startmap"].aliases == ("map",)

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)

def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_with(server, "\nquit\n")

def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)

def test_message():
    server = DummyServer()
    mod.message(server, "hello")

def test_backup():
    server = DummyServer()
    server.data["dir"] = "/tmp/test/"
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.backup(server)

def test_checkvalue_empty_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ())

def test_checkvalue_unsupported_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("totally_invalid_key_xyz",), "val")

def test_checkvalue_no_value():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("port",))

def test_checkvalue_port():
    server = DummyServer()
    result = mod.checkvalue(server, ("port",), "12345")
    assert result == 12345

def test_checkvalue_url():
    server = DummyServer()
    result = mod.checkvalue(server, ("url",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_download_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("download_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_version():
    server = DummyServer()
    result = mod.checkvalue(server, ("version",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
