"""Focused coverage tests for wreckfestserver."""

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.modules.pop("gamemodules.wreckfestserver", None)
with patch.dict(
    "sys.modules",
    {
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.wreckfestserver as mod
    from server import ServerError

    mod.runtime_module.send_to_server = MagicMock()


from tests.unit_tests.gamemodules.helpers import DummyServer


def test_configure_sets_wreckfest_defaults(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=33540, dir=str(tmp_path))
    assert server.data["configfile"] == "server_config.cfg"
    assert server.data["queryport"] == "27016"
    assert server.data["steamport"] == "27015"
    assert server.data["maxplayers"] == "24"


def test_sync_server_config_updates_official_keys(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "configfile": "server_config.cfg",
            "port": 33541,
            "queryport": 33542,
            "steamport": 33543,
            "servername": "AlphaGSM Wreckfest",
            "serverpassword": "secret",
            "maxplayers": 12,
        }
    )
    config_path = tmp_path / "server_config.cfg"
    config_path.write_text(
        "server_name=\n"
        "password=\n"
        "max_players=24\n"
        "steam_port=27015\n"
        "game_port=33540\n"
        "query_port=27016\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        "server_name=AlphaGSM Wreckfest",
        "password=secret",
        "max_players=12",
        "steam_port=33543",
        "game_port=33541",
        "query_port=33542",
    ]


def test_sync_server_config_without_install_dir_is_noop():
    server = DummyServer()
    server.data["queryport"] = 27016

    assert mod.sync_server_config(server) is None


def test_sync_server_config_seeds_vendor_initial_config(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "configfile": "server_config.cfg",
            "port": 33541,
            "queryport": 33542,
            "steamport": 33543,
        }
    )
    (tmp_path / "initial_server_config.cfg").write_text(
        "steam_port=27015\n"
        "game_port=33540\n"
        "query_port=27016\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert (tmp_path / "server_config.cfg").is_file()
    assert "game_port=33541" in (tmp_path / "server_config.cfg").read_text(encoding="utf-8")


def test_install_ensures_parent_appid_and_config(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "configfile": "server_config.cfg",
            "port": 33540,
            "queryport": 27016,
            "steamport": 27015,
            "Steam_AppID": 361580,
            "Steam_anonymous_login_possible": True,
        }
    )
    (tmp_path / "initial_server_config.cfg").write_text(
        "steam_port=27015\n"
        "game_port=33540\n"
        "query_port=27016\n",
        encoding="utf-8",
    )

    mod.install(server)

    assert (tmp_path / "steam_appid.txt").read_text(encoding="utf-8").strip() == "228380"
    assert (tmp_path / "server_config.cfg").is_file()


def test_get_query_address_uses_queryport():
    server = DummyServer()
    server.data["port"] = "33540"
    server.data["queryport"] = "27016"
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 33540, "tcp")
        assert mod.get_info_address(server) == ("127.0.0.1", 33540, "tcp")


def test_get_start_command_wraps_windows_payload_on_linux(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "Wreckfest_x64.exe",
            "configfile": "server_config.cfg",
            "wineprefix": str(tmp_path / "wineprefix"),
        }
    )
    (tmp_path / "Wreckfest_x64.exe").write_text("", encoding="utf-8")
    (tmp_path / "server_config.cfg").write_text("game_port=33540\n", encoding="utf-8")

    with patch.object(mod.proton, "wrap_command", return_value=["wrapped"]) as wrap_command:
        cmd, cwd = mod.get_start_command(server)

    wrap_command.assert_called_once()
    assert cmd == ["wrapped"]
    assert cwd == str(tmp_path)


def test_get_start_command_missing_exe_raises(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path), "exe_name": "missing.exe", "configfile": "server_config.cfg"})
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_prestart_refreshes_config(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "configfile": "server_config.cfg",
            "port": 33540,
            "queryport": 27016,
            "steamport": 27015,
        }
    )
    (tmp_path / "initial_server_config.cfg").write_text(
        "steam_port=27015\n"
        "game_port=33540\n"
        "query_port=27016\n",
        encoding="utf-8",
    )

    mod.prestart(server)

    assert (tmp_path / "steam_appid.txt").is_file()
    assert (tmp_path / "server_config.cfg").is_file()


def test_do_stop_uses_runtime_layer():
    server = DummyServer()
    mod.runtime_module.send_to_server.reset_mock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_once_with(server, "\003")


def test_restart_hook_stops_and_starts():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_checkvalue_supports_runtime_keys():
    server = DummyServer()
    assert mod.checkvalue(server, ("port",), "12345") == 12345
    assert mod.checkvalue(server, ("queryport",), "12346") == 12346
    assert mod.checkvalue(server, ("steamport",), "12347") == 12347
    assert mod.checkvalue(server, ("maxplayers",), "16") == 16
    assert mod.checkvalue(server, ("servername",), "AlphaGSM Wreckfest") == "AlphaGSM Wreckfest"
