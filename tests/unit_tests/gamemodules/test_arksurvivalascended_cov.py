"""Full coverage tests for arksurvivalascended."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer
import utils.proton as proton_module

sys.modules.pop('gamemodules.arksurvivalascended', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.arksurvivalascended as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    with patch.object(mod.secrets, "token_urlsafe", return_value="unique-rcon-secret"):
        mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data["adminpassword"] == "unique-rcon-secret"


@pytest.mark.parametrize("legacy_password", [None, "", "alphagsm"])
def test_prestart_replaces_missing_or_legacy_rcon_password(legacy_password, monkeypatch):
    server = DummyServer("asa")
    if legacy_password is not None:
        server.data["adminpassword"] = legacy_password
    monkeypatch.setattr(mod.secrets, "token_urlsafe", lambda _length: "new-secret")

    mod.prestart(server)

    assert server.data["adminpassword"] == "new-secret"
    assert server.data.saved == 1


def test_prestart_preserves_operator_rcon_password(monkeypatch):
    server = DummyServer("asa")
    server.data["adminpassword"] = "operator-secret"
    generate = MagicMock(side_effect=AssertionError("must preserve operator secret"))
    monkeypatch.setattr(mod.secrets, "token_urlsafe", generate)

    mod.prestart(server)

    assert server.data["adminpassword"] == "operator-secret"
    assert server.data.saved == 0


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["adminpassword"] = "test"
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["rconport"] = 27020
    server.data["serverpassword"] = "test"
    server.data["sessionname"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
    server.data["Steam_AppID"] = 2430930
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2430930
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2430930
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2430930
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
    exe_path = tmp_path / "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["adminpassword"] = "test"
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["serverpassword"] = "test"
    server.data["sessionname"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "ArkAscendedServer.exe",
        (
            "test?listen?SessionName=test?MaxPlayers=27015?RCONEnabled=True?RCONPort=27020"
            "?ServerPassword=test?ServerAdminPassword=test"
        ),
        "-port=27015",
        "-server",
        "-log",
    ]
    assert cwd == str(exe_path.parent)


def test_query_info_and_runtime_ports_use_udp_game_pair_and_rcon(monkeypatch):
    server = DummyServer("asa")
    server.data.update({"port": 7777, "queryport": 27015, "rconport": 27020})
    monkeypatch.setattr(
        mod.runtime_module,
        "resolve_query_host",
        lambda current: "10.0.0.9",
    )

    assert mod.get_query_address(server) == ("10.0.0.9", 27020, "source_rcon")
    assert mod.get_info_address(server) == ("10.0.0.9", 27020, "source_rcon")
    assert mod.port_claim_definitions == (
        {"key": "port", "protocol": "udp"},
        {"key": "rconport", "default": 27020, "protocol": "tcp"},
    )
    assert mod.get_runtime_requirements(server)["ports"] == [
        {"host": 7777, "container": 7777, "protocol": "udp"},
        {"host": 27020, "container": 27020, "protocol": "tcp"},
    ]


def test_legacy_queryport_is_not_claimed_after_rcon_migration(monkeypatch):
    from server.port_manager import collect_claim_set

    server = DummyServer("asa")
    server.module = mod
    server.data.update(
        {
            "port": 7777,
            "queryport": 27015,
            "rconport": 27020,
            "runtime": {"backend": "process"},
        }
    )
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda _server: "127.0.0.1")

    claims = collect_claim_set(server)
    ports = {endpoint.port for endpoint in claims.endpoints}

    assert 7777 in ports
    assert 27020 in ports
    assert 27015 not in ports


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["adminpassword"] = "test"
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["rconport"] = 27020
    server.data["serverpassword"] = "test"
    server.data["sessionname"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


def test_runtime_requirements_enable_xvfb_container_env():
    server = DummyServer()
    server.data["dir"] = "/srv/asa/"
    server.data["exe_name"] = "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
    server.data["port"] = 7777
    server.data["queryport"] = 27015

    requirements = mod.get_runtime_requirements(server)

    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["SDL_VIDEODRIVER"] == "x11"
    assert requirements["env"]["LIBGL_ALWAYS_SOFTWARE"] == "1"


def test_get_container_spec_delegates_windows_executable_to_proton_runtime(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
    exe_path = tmp_path / "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["adminpassword"] = "test"
    server.data["map"] = "TheIsland_WP"
    server.data["maxplayers"] = 70
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["serverpassword"] = ""
    server.data["sessionname"] = "AlphaGSM asa"

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == (
        proton_module.CONTAINER_SERVER_DIR + "/ShooterGame/Binaries/Win64"
    )
    assert spec["command"][0] == "./ArkAscendedServer.exe"
    assert spec["command"] == [
        "./ArkAscendedServer.exe",
        (
            "TheIsland_WP?listen?SessionName=AlphaGSM_asa?MaxPlayers=70"
            "?RCONEnabled=True?RCONPort=27020?ServerAdminPassword=test"
        ),
        "-port=7777",
        "-server",
        "-log",
    ]
    assert spec["ports"] == [
        {"host": 7777, "container": 7777, "protocol": "udp"},
        {"host": 27020, "container": 27020, "protocol": "tcp"},
    ]
    assert spec["env"]["ALPHAGSM_WINEPREFIX"] == (
        proton_module.CONTAINER_SERVER_DIR + "/.alphagsm-wineprefix"
    )
    assert spec["env"]["ALPHAGSM_XVFB"] == "1"


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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_map():
    server = DummyServer()
    result = mod.checkvalue(server, ("map",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_sessionname():
    server = DummyServer()
    result = mod.checkvalue(server, ("sessionname",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_adminpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("adminpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
