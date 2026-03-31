from types import SimpleNamespace

import importlib


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
