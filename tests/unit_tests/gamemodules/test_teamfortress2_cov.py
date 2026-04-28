"""Full coverage tests for teamfortress2."""

import importlib
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from utils.simple_kv_config import rewrite_space_config

sys.modules.pop('gamemodules.teamfortress2', None)
sys.modules.pop('gamemodules.teamfortress2.main', None)
with patch.dict('sys.modules', {'downloader': MagicMock(), 'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.fileutils': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.teamfortress2 as mod
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


def _tf2_package_root():
    return importlib.import_module("gamemodules.teamfortress2")


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data['port'] == 27015


def test_tf2_uses_shared_space_config_writer():
    assert mod.updateconfig is rewrite_space_config


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "srcds_run"
    server.data["Steam_AppID"] = 232250
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_install_disables_hibernation_during_integration(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAGSM_RUN_INTEGRATION", "1")
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "srcds_run"
    server.data["Steam_AppID"] = 232250
    server.data["Steam_anonymous_login_possible"] = True

    mod.install(server)

    cfg_text = (tmp_path / "tf" / "cfg" / "server.cfg").read_text()
    assert "sv_hibernate_when_empty 0" in cfg_text
    assert "tf_allow_server_hibernation 0" in cfg_text


def test_install_autoapplies_tf2_mods(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "srcds_run"
    server.data["Steam_AppID"] = 232250
    server.data["Steam_anonymous_login_possible"] = True
    server.data["mods"] = {
        "enabled": True,
        "autoapply": True,
        "desired": {
            "curated": [{"requested_id": "sourcemod", "resolved_id": "sourcemod.stable"}],
            "workshop": [],
        },
        "installed": [],
        "errors": [],
    }

    with patch.object(_tf2_package_root(), "doinstall", lambda server_obj: None), patch.object(
        _tf2_package_root(), "apply_configured_mods"
    ) as apply_mock:
        mod.install(server)

    apply_mock.assert_called_once_with(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 232250
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_autoapplies_tf2_mods(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 232250
    server.data["Steam_anonymous_login_possible"] = True
    server.data["mods"] = {
        "enabled": True,
        "autoapply": True,
        "desired": {
            "curated": [{"requested_id": "sourcemod", "resolved_id": "sourcemod.stable"}],
            "workshop": [],
        },
        "installed": [],
        "errors": [],
    }

    with patch.object(_tf2_package_root(), "apply_configured_mods") as apply_mock:
        mod.update(server, validate=False, restart=False)

    apply_mock.assert_called_once_with(server)


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 232250
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 232250
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
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
    server.data["startmap"] = "cp_dustbowl"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert "+tv_port" in cmd
    assert "27020" in cmd


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.screen.send_to_server.assert_called()


def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)


def test_tf2_status_warns_when_desired_mods_are_unapplied(capsys):
    server = DummyServer()
    server.data["mods"] = {
        "enabled": True,
        "autoapply": True,
        "desired": {
            "curated": [
                {"requested_id": "sourcemod", "resolved_id": "sourcemod.stable"}
            ],
            "workshop": [],
        },
        "installed": [],
        "errors": [],
    }

    mod.status(server, verbose=True)

    output = capsys.readouterr().out
    assert "mods pending apply" in output.lower()


def test_tf2_mod_apply_rejects_workshop_items_until_provider_is_verified(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["mods"] = {
        "enabled": True,
        "autoapply": True,
        "desired": {
            "curated": [],
            "workshop": [{"workshop_id": "1234567890", "source_type": "workshop"}],
        },
        "installed": [],
        "errors": [],
    }

    with pytest.raises(ServerError, match="Workshop support is experimental"):
        mod.command_functions["mod"](server, "apply")


def test_prestart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    mod.prestart(server)


def test_tf2_exposes_hibernating_console_info_hook():
    package_mod = importlib.import_module("gamemodules.teamfortress2")
    server = DummyServer()

    with patch.object(package_mod, '_tf2_hibernation_allowed', return_value=True, create=True), patch.object(
        package_mod, 'source_console_status', return_value={'name': 'AlphaGSM TF2 Server'}
    ):
        assert package_mod.get_hibernating_console_info(server) == {'name': 'AlphaGSM TF2 Server'}

    with patch.object(package_mod, '_tf2_hibernation_allowed', return_value=False, create=True):
        assert package_mod.get_hibernating_console_info(server) is None


def test_tf2_query_and_info_address_use_source_query_address():
    package_mod = importlib.import_module("gamemodules.teamfortress2")
    server = DummyServer()

    with patch.object(package_mod, 'source_query_address', return_value=('192.168.0.30', 27015, 'a2s')):
        assert package_mod.get_query_address(server) == ('192.168.0.30', 27015, 'a2s')
        assert package_mod.get_info_address(server) == ('192.168.0.30', 27015, 'a2s')


def test_tf2_exposes_schema_metadata_for_map_and_passwords():
    port_spec = mod.setting_schema["port"]
    map_spec = mod.setting_schema["map"]
    maxplayers_spec = mod.setting_schema["maxplayers"]
    rcon_spec = mod.setting_schema["rconpassword"]
    serverpassword_spec = mod.setting_schema["serverpassword"]

    assert mod.config_sync_keys == mod.VALVE_SERVER_CONFIG_SYNC_KEYS
    assert port_spec.launch_arg_tokens == ("-port",)
    assert map_spec.canonical_key == "map"
    assert map_spec.aliases == ("gamemap", "startmap", "level")
    assert map_spec.storage_key == "startmap"
    assert map_spec.launch_arg_tokens == ("+map",)
    assert maxplayers_spec.launch_arg_tokens == ("+maxplayers",)
    assert mod.setting_schema["servername"].native_config_key == "hostname"
    assert rcon_spec.native_config_key == "rcon_password"
    assert serverpassword_spec.native_config_key == "sv_password"
    assert rcon_spec.secret is True
    assert serverpassword_spec.secret is True
    assert rcon_spec.apply_to == ("datastore", "native_config")
    assert serverpassword_spec.apply_to == ("datastore", "native_config")


def test_sync_server_config_updates_server_cfg(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["servername"] = "AlphaGSM TF2"
    server.data["rconpassword"] = "rcon-secret"
    server.data["serverpassword"] = "server-secret"

    cfg_dir = tmp_path / "tf" / "cfg"
    cfg_dir.mkdir(parents=True)
    server_cfg = cfg_dir / "server.cfg"
    server_cfg.write_text(
        "// Team Fortress 2 server.cfg template\n"
        "// Place this file at: tf/cfg/server.cfg\n\n"
        'hostname "Old Name"\n'
        'sv_password "old"\n'
        'rcon_password "old"\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    config_text = server_cfg.read_text(encoding="utf-8")
    assert 'hostname "AlphaGSM TF2"' in config_text
    assert 'rcon_password "rcon-secret"' in config_text
    assert 'sv_password "server-secret"' in config_text


def test_list_setting_values_discovers_installed_tf2_maps(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    maps_dir = tmp_path / "tf" / "maps"
    maps_dir.mkdir(parents=True)
    (maps_dir / "cp_dustbowl.bsp").write_text("")
    (maps_dir / "cp_badlands.bsp").write_text("")

    assert mod.list_setting_values(server, "map") == ["cp_badlands", "cp_dustbowl"]
    assert mod.list_setting_values(server, "servername") is None


def test_checkvalue_startmap_validates_installed_tf2_maps(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    maps_dir = tmp_path / "tf" / "maps"
    maps_dir.mkdir(parents=True)
    (maps_dir / "cp_dustbowl.bsp").write_text("")

    assert mod.checkvalue(server, ("startmap",), "cp_dustbowl") == "cp_dustbowl"

    with pytest.raises(ServerError, match="Unsupported map cp_missing"):
        mod.checkvalue(server, ("startmap",), "cp_missing")


def test_checkvalue_accepts_basic_tf2_keys(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"

    assert mod.checkvalue(server, ("port",), "27016") == 27016
    assert mod.checkvalue(server, ("maxplayers",), "32") == "32"
    assert mod.checkvalue(server, ("servername",), "TF2 Server") == "TF2 Server"
    assert mod.checkvalue(server, ("rconpassword",), "secret") == "secret"
    assert mod.checkvalue(server, ("serverpassword",), "secret") == "secret"
    assert mod.checkvalue(server, ("exe_name",), "srcds_run_64") == "srcds_run_64"
