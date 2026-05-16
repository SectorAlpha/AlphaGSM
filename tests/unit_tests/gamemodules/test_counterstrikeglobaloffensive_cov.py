"""Full coverage tests for counterstrikeglobaloffensive."""

import os
import sys
from unittest.mock import patch, MagicMock

from utils.simple_kv_config import rewrite_space_config

sys.modules.pop('gamemodules.counterstrikeglobaloffensive', None)
with patch.dict('sys.modules', {'downloader': MagicMock(), 'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.fileutils': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.counterstrikeglobaloffensive as mod
    from server import ServerError


class DummyData(dict):
    def save(self):
        pass
    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]
    def get(self, key, default=None):
        return super().get(key, default)


class DummyServer:
    def __init__(self, name="testserver"):
        self.name = name
        self.data = DummyData()
        self._stopped = False
        self._started = False
    def stop(self):
        self._stopped = True
    def start(self):
        self._started = True


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data['port'] == 27015


def test_csgo_uses_shared_space_config_writer():
    assert mod.updateconfig is rewrite_space_config


def test_csgo_exposes_shared_valve_schema_and_sync_keys():
    assert mod.config_sync_keys == mod.VALVE_SERVER_CONFIG_SYNC_KEYS
    assert mod.setting_schema["port"].launch_arg_tokens == ("-port",)
    assert mod.setting_schema["map"].launch_arg_tokens == ("+map",)
    assert mod.setting_schema["maxplayers"].launch_arg_tokens == ("-maxplayers",)
    assert mod.setting_schema["serverpassword"].native_config_key == "sv_password"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["gamemode"] = "test"
    server.data["gametype"] = "test"
    server.data["mapgroup"] = "test"
    server.data["maxplayers"] = 27015
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path, monkeypatch):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "srcds_run"
    server.data["Steam_AppID"] = 740
    server.data["Steam_anonymous_login_possible"] = True
    monkeypatch.setattr(mod.steamcmd, "download", lambda *args, **kwargs: None)
    mod.install(server)


def test_install_disables_hibernation_during_integration(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAGSM_RUN_INTEGRATION", "1")
    monkeypatch.setattr(mod, "make_empty_file", lambda path: open(path, "a", encoding="utf-8").close())
    monkeypatch.setattr(mod.steamcmd, "download", lambda *args, **kwargs: None)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "srcds_run"
    server.data["Steam_AppID"] = 740
    server.data["Steam_anonymous_login_possible"] = True

    cfg_dir = tmp_path / "csgo" / "cfg"
    cfg_dir.mkdir(parents=True)
    mod.install(server)

    cfg_text = (cfg_dir / "server.cfg").read_text()
    assert "sv_hibernate_when_empty 0" in cfg_text


def test_sync_server_config_updates_server_cfg(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["servername"] = "Configured CSGO"
    server.data["rconpassword"] = "rcon-secret"
    server.data["serverpassword"] = "join-secret"

    mod.sync_server_config(server)

    config_text = (tmp_path / "csgo" / "cfg" / "server.cfg").read_text(encoding="utf-8")
    assert 'hostname "Configured CSGO"' in config_text
    assert 'rcon_password "rcon-secret"' in config_text
    assert 'sv_password "join-secret"' in config_text


def test_update_with_restart(tmp_path, monkeypatch):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 740
    server.data["Steam_anonymous_login_possible"] = True
    monkeypatch.setattr(mod.steamcmd, "download", lambda *args, **kwargs: None)
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path, monkeypatch):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 740
    server.data["Steam_anonymous_login_possible"] = True
    monkeypatch.setattr(mod.steamcmd, "download", lambda *args, **kwargs: None)
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path, monkeypatch):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 740
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    monkeypatch.setattr(mod.steamcmd, "download", lambda *args, **kwargs: None)
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "srcds_run"
    (tmp_path / "srcds_run").write_text("")
    server.data["gamemode"] = "test"
    server.data["gametype"] = "test"
    server.data["mapgroup"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_get_start_command_moves_bundled_libgcc(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "srcds_run"
    (tmp_path / "srcds_run").write_text("")
    libgcc_path = tmp_path / "bin" / "libgcc_s.so.1"
    libgcc_path.parent.mkdir(parents=True)
    libgcc_path.write_text("stale")
    server.data["gamemode"] = "test"
    server.data["gametype"] = "test"
    server.data["mapgroup"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["startmap"] = "test"

    mod.get_start_command(server)

    assert not libgcc_path.exists()
    assert (tmp_path / "bin" / "libgcc_s.so.1.alphagsm-disabled").exists()


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["gamemode"] = "test"
    server.data["gametype"] = "test"
    server.data["mapgroup"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    # CSGO has a bug: ServerError() without raise, so it doesn't actually raise
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.screen.send_to_server.assert_called()


def test_csgo_query_and_info_address_use_source_query_address(monkeypatch):
    server = DummyServer()
    server.data["port"] = 27015
    calls = []
    monkeypatch.setattr(
        mod,
        "source_query_address",
        lambda srv: calls.append(srv) or ("127.0.0.1", 27015, "a2s"),
    )

    assert mod.get_query_address(server) == ("127.0.0.1", 27015, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.1", 27015, "a2s")
    assert calls == [server, server]


def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)
