"""Full coverage tests for cod4server."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.cod4server', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.cod4server as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=28960, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip")
    assert server.data['port'] == 28960

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 28960
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["28961", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)


COD4X_RELEASE_URL = (
    "https://github.com/callofduty4x/CoD4x_Server/releases/download/21.2/cod4x18_dedrun"
)
STEAM_MP_MAPS = [
    "mp_backlot", "mp_bloc", "mp_bog", "mp_broadcast", "mp_carentan",
    "mp_cargoship", "mp_citystreets", "mp_convoy", "mp_countdown", "mp_crash",
    "mp_crash_snow", "mp_creek", "mp_crossfire", "mp_farm", "mp_killhouse",
    "mp_overgrown", "mp_pipeline", "mp_shipment", "mp_showdown", "mp_strike",
    "mp_vacant",
]


def test_configure_defaults_to_cod4x_release_binary(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=28960, dir=str(tmp_path))
    assert server.data["exe_name"] == "cod4x18_dedrun"
    assert server.data["url"] == COD4X_RELEASE_URL
    assert server.data["download_name"] == "cod4x18_dedrun"


def test_install_accepts_steam_fastfiles_without_filesyscheck(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod4x18_dedrun"
    server.data["url"] = COD4X_RELEASE_URL
    server.data["download_name"] = "cod4x18_dedrun"
    recipe = mod.get_asset_requirements(server)
    assert recipe["multiplayer_maps"] == STEAM_MP_MAPS

    def fake_install_binary(_server):
        binary = tmp_path / "cod4x18_dedrun"
        binary.write_bytes(b"elf")
        binary.chmod(0o644)
        (tmp_path / "libstdc++.so.6").write_bytes(b"oldstd")
        (tmp_path / "libgcc_s.so.1").write_bytes(b"oldgcc")
        (tmp_path / "pbsetup.run").write_bytes(b"redist")
        main_dir = tmp_path / "main"
        main_dir.mkdir()
        (main_dir / "iw_00.iwd").write_bytes(b"iwd")
        zone = tmp_path / "zone" / "english"
        zone.mkdir(parents=True)
        for name in (
            "localized_common_mp.ff",
            "localized_code_post_gfx_mp.ff",
            "code_post_gfx_mp.ff",
            "common_mp.ff",
            "ui_mp.ff",
        ):
            (zone / name).write_bytes(b"ff")
        for name in STEAM_MP_MAPS:
            (zone / f"{name}.ff").write_bytes(b"map")

    mod.install_binary = MagicMock(side_effect=fake_install_binary)
    mod.install(server)
    mod.install_binary.side_effect = None

    exe = tmp_path / "cod4x18_dedrun"
    assert exe.is_file()
    assert exe.stat().st_mode & 0o111
    assert not (tmp_path / "fileSysCheck.cfg").exists()
    assert not (tmp_path / "libstdc++.so.6").exists()
    assert not (tmp_path / "libgcc_s.so.1").exists()
    assert not (tmp_path / "pbsetup.run").exists()
    assert (tmp_path / "main" / "iw_00.iwd").is_file()
    assert (tmp_path / "zone" / "english" / "localized_common_mp.ff").is_file()
    for name in STEAM_MP_MAPS:
        assert (tmp_path / "zone" / "english" / f"{name}.ff").is_file()


def test_get_start_command_uses_cod4x_without_bundled_runtime(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod4x18_dedrun"
    (tmp_path / "cod4x18_dedrun").write_text("")
    server.data["hostname"] = "test"
    server.data["moddir"] = "main"
    server.data["port"] = 28960
    server.data["startmap"] = "mp_crash"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./cod4x18_dedrun",
        "+set",
        "dedicated",
        "2",
        "+set",
        "sv_punkbuster",
        "0",
        "+set",
        "fs_basepath",
        ".",
        "+set",
        "fs_homepath",
        ".",
        "+set",
        "sv_hostname",
        "test",
        "+set",
        "net_port",
        "28960",
        "+map",
        "mp_crash",
    ]
    assert cwd == server.data["dir"]
    assert "libstdc++.so.5" not in cmd
    assert "LD_LIBRARY_PATH=." not in cmd
    assert "sv_authtoken" not in cmd
    assert mod.get_query_address(server) == (
        mod.get_query_address(server)[0],
        28960,
        "quake",
    )
    assert mod.get_info_address(server) == mod.get_query_address(server)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod4x18_dedrun"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"

    def fake_install_binary(_server):
        binary = tmp_path / "cod4x18_dedrun"
        binary.write_bytes(b"elf")
        binary.chmod(0o644)
        (tmp_path / "fileSysCheck.cfg").write_text("", encoding="utf-8")
        main_dir = tmp_path / "main"
        main_dir.mkdir()
        (main_dir / "localized_english_iw00.iwd").write_text("", encoding="utf-8")

    mod.install_binary.side_effect = fake_install_binary
    mod.install(server)
    mod.install_binary.side_effect = None
    assert os.access(tmp_path / "cod4x18_dedrun", os.X_OK)


def test_install_rejects_missing_base_assets(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod4x18_dedrun"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"

    def fake_install_binary(_server):
        main_dir = tmp_path / "main"
        main_dir.mkdir()
        (main_dir / "iw_12.iwd").write_text("", encoding="utf-8")

    mod.install_binary.side_effect = fake_install_binary
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\): cod4server"):
        mod.install(server)
    mod.install_binary.side_effect = None

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod4x18_dedrun"
    (tmp_path / "cod4x18_dedrun").write_text("")
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./cod4x18_dedrun",
        "+set",
        "dedicated",
        "2",
        "+set",
        "sv_punkbuster",
        "0",
        "+set",
        "fs_basepath",
        ".",
        "+set",
        "fs_homepath",
        ".",
        "+set",
        "fs_game",
        "test",
        "+set",
        "sv_hostname",
        "test",
        "+set",
        "net_port",
        "27015",
        "+map",
        "test",
    ]
    assert cwd == server.data["dir"]
    assert mod.get_query_address(server)[2] == "quake"
    assert "libstdc++.so.5" not in cmd
    assert "LD_LIBRARY_PATH=." not in cmd


def test_install_drops_punkbuster_and_old_runtime_libs(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod4x18_dedrun"
    server.data["url"] = mod.COD4_SERVER_URL
    server.data["download_name"] = mod.COD4_SERVER_NAME

    def fake_install_binary(_server):
        binary = tmp_path / "cod4x18_dedrun"
        binary.write_bytes(b"elf")
        binary.chmod(0o644)
        (tmp_path / "libstdc++.so.6").write_bytes(b"std6")
        (tmp_path / "libgcc_s.so.1").write_bytes(b"gcc")
        (tmp_path / "pbsetup.run").write_bytes(b"redist")
        (tmp_path / "fileSysCheck.cfg").write_text("", encoding="utf-8")
        main_dir = tmp_path / "main"
        main_dir.mkdir()
        (main_dir / "iw_12.iwd").write_bytes(b"iwd")
        (main_dir / "localized_english_iw00.iwd").write_bytes(b"loc")
        zone_dir = tmp_path / "zone" / "english"
        zone_dir.mkdir(parents=True)
        (zone_dir / "code_post_gfx_mp.ff").write_bytes(b"ff")

    mod.install_binary.side_effect = fake_install_binary
    mod.install(server)
    mod.install_binary.side_effect = None

    assert (tmp_path / "cod4x18_dedrun").is_file()
    assert os.access(tmp_path / "cod4x18_dedrun", os.X_OK)
    assert not (tmp_path / "libstdc++.so.6").exists()
    assert not (tmp_path / "libgcc_s.so.1").exists()
    assert (tmp_path / "main" / "iw_12.iwd").is_file()
    assert (tmp_path / "main" / "localized_english_iw00.iwd").is_file()
    assert (tmp_path / "zone" / "english" / "code_post_gfx_mp.ff").read_bytes() == b"ff"
    assert not (tmp_path / "pbsetup.run").exists()
    assert not (tmp_path / "libstdc++.so.5").exists()


def test_setting_schema_exposes_cod4_launch_tokens():
    assert mod.setting_schema["fs_game"].canonical_key == "moddir"
    assert mod.setting_schema["fs_game"].launch_arg_tokens == ("+set", "fs_game")
    assert mod.setting_schema["hostname"].launch_arg_tokens == ("+set", "sv_hostname")
    assert mod.setting_schema["port"].launch_arg_tokens == ("+set", "net_port")


def test_sync_server_config_updates_mod_server_cfg(tmp_path):
    server = DummyServer("cod4")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "moddir": "main",
            "hostname": "AlphaGSM cod4",
            "startmap": "mp_backlot",
        }
    )
    cfg_dir = tmp_path / "main"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "server.cfg"
    cfg_path.write_text(
        'hostname="Old Name"\nmoddir=mods\nstartmap=mp_crash\nset sv_punkbuster 1\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert cfg_path.read_text(encoding="utf-8") == (
        'hostname="AlphaGSM cod4"\n'
        'moddir=main\n'
        'startmap=mp_backlot\n'
        'set sv_punkbuster 1\n'
    )

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)

def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()

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

def test_checkvalue_moddir():
    server = DummyServer()
    result = mod.checkvalue(server, ("moddir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
