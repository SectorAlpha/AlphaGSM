import importlib
from types import SimpleNamespace


class FakeSection(dict):
    def __init__(self, values=None, sections=None):
        super().__init__({} if values is None else values)
        self._sections = {} if sections is None else sections

    def getsection(self, key, **kwargs):
        return self._sections.get(key, FakeSection())


def test_findmodule_loads_real_valve_module():
    server_module = importlib.import_module("server.server")

    true_name, module = server_module._findmodule("csczserver")

    assert true_name == "csczserver"
    assert module.__name__ == "gamemodules.csczserver"


def test_source_module_configure_and_start_command(tmp_path):
    module = importlib.import_module("gamemodules.cssserver")
    server = SimpleNamespace(name="cssalpha", data={})

    module.configure(server, False, 28015, str(tmp_path / "css"))
    install_dir = tmp_path / "css"
    install_dir.mkdir()
    (install_dir / "srcds_run").write_text("")

    cmd, cwd = module.get_start_command(server)

    assert cwd == server.data["dir"]
    assert cmd[:4] == ["./srcds_run", "-game", "cstrike", "-strictportbind"]
    assert "+map" in cmd
    assert "de_dust2" in cmd
    assert server.data["port"] == 28015
    assert server.data["backupfiles"] == ["cstrike", "cstrike/cfg/server.cfg"]


def test_goldsrc_module_update_uses_mod_aware_steamcmd(monkeypatch, tmp_path):
    module = importlib.import_module("gamemodules.csserver")
    steamcmd_module = importlib.import_module("utils.steamcmd")
    server = SimpleNamespace(name="csalpha", data={})
    calls = []

    module.configure(server, False, 27015, str(tmp_path / "cs"))
    monkeypatch.setattr(
        steamcmd_module,
        "download",
        lambda path, app_id, anon, validate=True, mod=None: calls.append(
            (path, app_id, anon, validate, mod)
        ),
    )

    module.update(server, validate=True, restart=False)

    assert calls == [(server.data["dir"], 90, True, True, "cstrike")]


def test_valve_module_configure_uses_alphagsm_config_defaults(monkeypatch, tmp_path):
    module = importlib.import_module("gamemodules.cssserver")
    valve_server = importlib.import_module("utils.valve_server")
    fake_settings = SimpleNamespace(
        user=FakeSection(
            sections={
                "gamemodules": FakeSection(
                    sections={
                        "cssserver": FakeSection(
                            {
                                "startmap": "de_nuke",
                                "maxplayers": "24",
                                "port": "29015",
                                "clientport": "29016",
                                "server_cfg": "alpha.cfg",
                                "dir": str(tmp_path / "configured-css"),
                            }
                        )
                    }
                )
            }
        )
    )
    monkeypatch.setattr(valve_server, "settings", fake_settings)
    server = SimpleNamespace(name="cssalpha", data={})

    module.configure(server, False)

    assert server.data["startmap"] == "de_nuke"
    assert server.data["maxplayers"] == "24"
    assert server.data["port"] == 29015
    assert server.data["clientport"] == 29016
    assert server.data["server_cfg"] == "alpha.cfg"
    assert server.data["dir"] == str(tmp_path / "configured-css") + "/"
    assert server.data["backupfiles"] == ["cstrike", "cstrike/cfg/server.cfg"]


def test_valve_module_install_updates_server_cfg_from_settings(monkeypatch, tmp_path):
    module = importlib.import_module("gamemodules.cssserver")
    valve_server = importlib.import_module("utils.valve_server")
    fake_settings = SimpleNamespace(
        user=FakeSection(
            sections={
                "gamemodules": FakeSection(
                    sections={
                        "cssserver": FakeSection(
                            sections={
                                "servercfg": FakeSection(
                                    {"hostname": "\"Configured CSS\"", "sv_pure": "1"}
                                )
                            }
                        )
                    }
                )
            }
        )
    )
    monkeypatch.setattr(valve_server, "settings", fake_settings)
    monkeypatch.setattr(valve_server.steamcmd, "download", lambda *args, **kwargs: None)
    server = SimpleNamespace(
        name="cssalpha",
        data={"dir": str(tmp_path) + "/", "exe_name": "srcds_run", "server_cfg": "server.cfg"},
    )

    module.install(server)

    cfg_path = tmp_path / "cstrike" / "cfg" / "server.cfg"
    cfg_text = cfg_path.read_text()
    assert 'hostname "Configured CSS"' in cfg_text
    assert "sv_pure 1" in cfg_text


def test_valve_source_install_disables_hibernation_for_integration(monkeypatch, tmp_path):
    module = importlib.import_module("gamemodules.cssserver")
    valve_server = importlib.import_module("utils.valve_server")
    monkeypatch.setenv("ALPHAGSM_RUN_INTEGRATION", "1")
    monkeypatch.setattr(valve_server.steamcmd, "download", lambda *args, **kwargs: None)
    server = SimpleNamespace(
        name="cssalpha",
        data={"dir": str(tmp_path) + "/", "exe_name": "srcds_run", "server_cfg": "server.cfg"},
    )

    module.install(server)

    cfg_path = tmp_path / "cstrike" / "cfg" / "server.cfg"
    assert "sv_hibernate_when_empty 0" in cfg_path.read_text()


def test_valve_source_module_exposes_wake_hook(monkeypatch):
    module = importlib.import_module("gamemodules.cssserver")
    valve_server = importlib.import_module("utils.valve_server")
    calls = []
    server = SimpleNamespace(name="cssalpha", data={})

    monkeypatch.setattr(
        valve_server.screen,
        "send_to_server",
        lambda name, payload: calls.append((name, payload)),
    )

    delay = module.MODULE.wake_a2s_query(server)

    assert delay == 1.0
    assert calls == [("cssalpha", "\nstatus\n")]


def test_parse_source_console_status_returns_latest_complete_block():
    valve_server = importlib.import_module("utils.valve_server")

    parsed = valve_server.parse_source_console_status(
        """
status
hostname: Old Server
map     : de_dust2 at: 0 x, 0 y, 0 z
players : 1 humans, 0 bots (16 max)
status
hostname: AlphaGSM TF2 Server
version : 10515055/24 10515055 secure
udp/ip  : ?.?.?.?:?  (public IP from Steam: 82.10.131.108)
steamid : [A:1:1244653586:49343] (90283920363350034)
map     : cp_dustbowl at: 0 x, 0 y, 0 z
players : 0 humans, 0 bots (16 max)
"""
    )

    assert parsed == {
        "name": "AlphaGSM TF2 Server",
        "version": "10515055/24 10515055 secure",
        "address": "?.?.?.?:?  (public IP from Steam: 82.10.131.108)",
        "steamid": "[A:1:1244653586:49343] (90283920363350034)",
        "map": "cp_dustbowl",
        "players": 0,
        "bots": 0,
        "max_players": 16,
    }


def test_source_console_status_collects_new_log_output(monkeypatch, tmp_path):
    valve_server = importlib.import_module("utils.valve_server")
    log_file = tmp_path / "server.log"
    log_file.write_text("existing\n", encoding="utf-8")
    server = SimpleNamespace(name="cssalpha", data={})

    def fake_send_to_server(_name, _payload):
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(
                "status\n"
                "hostname: AlphaGSM TF2 Server\n"
                "version : 10515055/24 10515055 secure\n"
                "udp/ip  : ?.?.?.?:?  (public IP from Steam: 82.10.131.108)\n"
                "steamid : [A:1:1244653586:49343] (90283920363350034)\n"
                "map     : cp_dustbowl at: 0 x, 0 y, 0 z\n"
                "players : 0 humans, 0 bots (16 max)\n"
            )

    monkeypatch.setattr(valve_server.screen, "logpath", lambda _name: str(log_file))
    monkeypatch.setattr(valve_server.screen, "send_to_server", fake_send_to_server)
    monkeypatch.setattr(valve_server.time, "sleep", lambda *_args: None)

    parsed = valve_server.source_console_status(server, timeout=1.0)

    assert parsed["name"] == "AlphaGSM TF2 Server"
    assert parsed["map"] == "cp_dustbowl"
    assert parsed["players"] == 0


def test_hibernating_source_console_info_returns_none_when_address_is_bound(monkeypatch):
    valve_server = importlib.import_module("utils.valve_server")
    server = SimpleNamespace(name="cssalpha", data={})

    monkeypatch.setattr(
        valve_server,
        "source_console_status",
        lambda _server, timeout=5.0: {
            "name": "AlphaGSM TF2 Server",
            "version": "10515055/24 10515055 secure",
            "address": "0.0.0.0:27015",
            "map": "cp_dustbowl",
            "players": 0,
            "bots": 0,
            "max_players": 16,
        },
    )

    assert valve_server.hibernating_source_console_info(server) is None
