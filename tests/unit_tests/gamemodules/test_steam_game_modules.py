import importlib
import sys

import gamemodules.counterstrikeglobaloffensive as csgo
import gamemodules.counterstrike2 as cs2
import gamemodules.teamfortress2 as tf2


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="alpha"):
        self.name = name
        self.data = DummyData()
        self.stop_calls = 0
        self.start_calls = 0

    def stop(self):
        self.stop_calls += 1

    def start(self):
        self.start_calls += 1


def _tf2_package_root():
    return importlib.import_module("gamemodules.teamfortress2")


def test_tf2_configure_populates_defaults_and_backup_schedule(tmp_path):
    server = DummyServer()

    args, kwargs = tf2.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["Steam_AppID"] == tf2.steam_app_id
    assert server.data["Steam_anonymous_login_possible"] is True
    assert server.data["port"] == 27015
    assert server.data["dir"].endswith("/")
    assert "default" in server.data["backup"]["profiles"]
    assert server.data["backup"]["schedule"]
    assert server.data.saved == 1


def test_csgo_configure_populates_game_defaults(tmp_path):
    server = DummyServer()

    csgo.configure(server, ask=False, port=27016, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == csgo.steam_app_id
    assert server.data["mapgroup"] == "mg_active"
    assert server.data["startmap"] == "de_dust2"
    assert server.data["maxplayers"] == "16"
    assert server.data["port"] == 27016


def test_tf2_install_creates_config_file_when_missing(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "Steam_AppID": 1, "Steam_anonymous_login_possible": True, "exe_name": "srcds_run"})
    cfg_path = tmp_path / "tf" / "cfg" / "server.cfg"
    launcher = tmp_path / "srcds_run_64"
    launcher.write_text("")
    doinstall_calls = []
    monkeypatch.setattr(
        _tf2_package_root(),
        "doinstall",
        lambda server_obj: doinstall_calls.append(server_obj),
    )

    tf2.install(server)

    assert doinstall_calls == [server]
    assert cfg_path.exists()
    assert 'hostname "AlphaGSM TF2 Server"' in cfg_path.read_text()
    assert server.data["exe_name"] == "srcds_run_64"


def test_tf2_install_applies_mods_when_autoapply_enabled(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "Steam_AppID": 1,
            "Steam_anonymous_login_possible": True,
            "exe_name": "srcds_run",
            "mods": {
                "enabled": True,
                "autoapply": True,
                "desired": {
                    "curated": [
                        {
                            "requested_id": "sourcemod",
                            "resolved_id": "sourcemod.stable",
                        }
                    ],
                    "workshop": [],
                },
                "installed": [],
                "errors": [],
            },
        }
    )
    calls = []

    monkeypatch.setattr(_tf2_package_root(), "doinstall", lambda server_obj: calls.append("base"))
    monkeypatch.setattr(
        _tf2_package_root(),
        "apply_configured_mods",
        lambda server_obj: calls.append("mods"),
    )

    tf2.install(server)

    assert calls == ["base", "mods"]


def test_csgo_install_creates_config_file_when_missing(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "Steam_AppID": 1, "Steam_anonymous_login_possible": True})
    cfg_path = tmp_path / "csgo" / "cfg" / "server.cfg"
    cfg_path.parent.mkdir(parents=True)
    calls = []

    monkeypatch.setattr(csgo, "doinstall", lambda server_obj: calls.append(server_obj))
    monkeypatch.setattr(csgo, "make_empty_file", lambda path: calls.append(path))

    csgo.install(server)

    assert calls[0] is server
    assert calls[1] == str(cfg_path)


def test_tf2_get_start_command_prefixes_executable_and_uses_steamcmd(tmp_path, monkeypatch):
    server = DummyServer("blue")
    exe_path = tmp_path / "srcds_run"
    exe_path.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "srcds_run",
            "port": 27015,
            "maxplayers": "24",
            "startmap": "cp_dustbowl",
        }
    )

    monkeypatch.setattr(tf2.os.path, "isfile", lambda path: True)

    command, cwd = tf2.get_start_command(server)

    assert command[0] == "./srcds_run"
    assert "+clientport" in command
    assert "27016" in command
    assert "+tv_port" in command
    assert "27020" in command
    assert "+map" in command
    assert "cp_dustbowl" in command
    assert "+servercfgfile" in command
    assert "server.cfg" in command
    assert cwd == server.data["dir"]


def test_tf2_get_start_command_falls_back_to_64_bit_launcher(tmp_path, monkeypatch):
    server = DummyServer("blue")
    launcher = tmp_path / "srcds_run_64"
    launcher.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "srcds_run",
            "port": 27015,
            "maxplayers": "24",
            "startmap": "cp_dustbowl",
        }
    )

    command, cwd = tf2.get_start_command(server)

    assert command[0] == "./srcds_run_64"
    assert server.data["exe_name"] == "srcds_run_64"
    assert "27016" in command
    assert "27020" in command
    assert "cp_dustbowl" in command
    assert cwd == server.data["dir"]


def test_csgo_get_start_command_prefixes_executable_and_uses_steamcmd(tmp_path, monkeypatch):
    server = DummyServer("red")
    exe_path = tmp_path / "srcds_run"
    exe_path.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "srcds_run",
            "port": 27016,
            "maxplayers": "16",
            "gametype": "0",
            "gamemode": "1",
            "mapgroup": "mg_active",
            "startmap": "de_dust2",
        }
    )

    monkeypatch.setattr(csgo.os.path, "isfile", lambda path: True)
    monkeypatch.setattr(csgo.steamcmd, "get_autoupdate_script", lambda name, path, app_id: "/tmp/update.txt")
    monkeypatch.setattr(csgo.steamcmd, "STEAMCMD_DIR", "/tmp/steamcmd")

    command, cwd = csgo.get_start_command(server)

    assert command[0] == "./srcds_run"
    assert "-game" in command
    assert "csgo" in command
    assert cwd == server.data["dir"]


def test_csgo_get_start_command_disables_bundled_libgcc(tmp_path, monkeypatch):
    server = DummyServer("red")
    exe_path = tmp_path / "srcds_run"
    exe_path.write_text("")
    libgcc_path = tmp_path / "bin" / "libgcc_s.so.1"
    libgcc_path.parent.mkdir(parents=True)
    libgcc_path.write_text("stale-libgcc")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "srcds_run",
            "port": 27016,
            "maxplayers": "16",
            "gametype": "0",
            "gamemode": "1",
            "mapgroup": "mg_active",
            "startmap": "de_dust2",
        }
    )

    monkeypatch.setattr(csgo.steamcmd, "get_autoupdate_script", lambda name, path, app_id: "/tmp/update.txt")
    monkeypatch.setattr(csgo.steamcmd, "STEAMCMD_DIR", "/tmp/steamcmd")

    command, cwd = csgo.get_start_command(server)

    assert command[0] == "./srcds_run"
    assert cwd == server.data["dir"]
    assert not libgcc_path.exists()
    assert (tmp_path / "bin" / "libgcc_s.so.1.alphagsm-disabled").exists()


def test_steam_game_restart_calls_stop_then_start():
    server = DummyServer()

    tf2.restart(server)
    csgo.restart(server)

    assert server.stop_calls == 2
    assert server.start_calls == 2


def test_steam_game_update_downloads_and_optionally_restarts(monkeypatch):
    tf2_server = DummyServer()
    tf2_server.data["dir"] = "/srv/tf2/"
    csgo_server = DummyServer()
    csgo_server.data["dir"] = "/srv/csgo/"
    calls = []

    monkeypatch.setattr(
        tf2.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    tf2.update(tf2_server, validate=True, restart=True)
    csgo.update(csgo_server, validate=False, restart=False)

    assert ("/srv/tf2/", tf2.steam_app_id, tf2.steam_anonymous_login_possible, True) in calls
    assert ("/srv/csgo/", csgo.steam_app_id, csgo.steam_anonymous_login_possible, False) in calls
    assert tf2_server.start_calls == 1
    assert csgo_server.start_calls == 0


def test_tf2_update_applies_mods_when_autoapply_enabled(monkeypatch):
    tf2_server = DummyServer()
    tf2_server.data.update(
        {
            "dir": "/srv/tf2/",
            "mods": {
                "enabled": True,
                "autoapply": True,
                "desired": {
                    "curated": [
                        {
                            "requested_id": "sourcemod",
                            "resolved_id": "sourcemod.stable",
                        }
                    ],
                    "workshop": [],
                },
                "installed": [],
                "errors": [],
            },
        }
    )
    calls = []

    monkeypatch.setattr(
        tf2.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append(("base", path, validate)),
    )
    monkeypatch.setattr(
        _tf2_package_root(),
        "apply_configured_mods",
        lambda server_obj: calls.append(("mods", server_obj.data["dir"])),
    )

    tf2.update(tf2_server, validate=True, restart=False)

    assert calls == [("base", "/srv/tf2/", True), ("mods", "/srv/tf2/")]


def test_tf2_prestart_links_64_bit_steamclient(tmp_path, monkeypatch):
    package_tf2 = importlib.import_module("gamemodules.teamfortress2")
    server = DummyServer()
    steam_root = tmp_path / "steam"
    sdk_dir = tmp_path / ".steam" / "sdk64"
    steamclient_src = steam_root / "linux64" / "steamclient.so"
    steamclient_src.parent.mkdir(parents=True)
    steamclient_src.write_text("")

    monkeypatch.setattr(package_tf2.steamcmd, "STEAMCMD_DIR", str(steam_root) + "/")
    monkeypatch.setattr(package_tf2, "STEAMCLIENT_DST", str(sdk_dir / "steamclient.so"))

    package_tf2.prestart(server)

    assert (sdk_dir / "steamclient.so").is_symlink()
    assert (sdk_dir / "steamclient.so").resolve() == steamclient_src


def test_tf2_runtime_wrappers_use_steamcmd_linux_family(tmp_path):
    server = DummyServer("blue")
    launcher = tmp_path / "srcds_run"
    launcher.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "srcds_run",
            "port": 27015,
            "maxplayers": "24",
            "startmap": "cp_dustbowl",
        }
    )

    requirements = tf2.get_runtime_requirements(server)
    spec = tf2.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27015, "container": 27015, "protocol": "tcp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./srcds_run"


def test_csgo_runtime_wrappers_use_steamcmd_linux_family(tmp_path, monkeypatch):
    server = DummyServer("red")
    launcher = tmp_path / "srcds_run"
    launcher.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "srcds_run",
            "port": 27016,
            "maxplayers": "16",
            "gametype": "0",
            "gamemode": "1",
            "mapgroup": "mg_active",
            "startmap": "de_dust2",
        }
    )

    monkeypatch.setattr(csgo.steamcmd, "get_autoupdate_script", lambda name, path, app_id: "/tmp/update.txt")
    monkeypatch.setattr(csgo.steamcmd, "STEAMCMD_DIR", "/tmp/steamcmd")

    requirements = csgo.get_runtime_requirements(server)
    spec = csgo.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 27016, "container": 27016, "protocol": "udp"},
        {"host": 27016, "container": 27016, "protocol": "tcp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./srcds_run"


def test_cs2_runtime_wrappers_use_steamcmd_linux_family(tmp_path):
    server = DummyServer("cs2")
    launcher = tmp_path / "game" / "cs2.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "game/cs2.sh",
            "port": 27015,
            "maxplayers": "24",
            "startmap": "de_dust2",
        }
    )

    requirements = cs2.get_runtime_requirements(server)
    spec = cs2.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27015, "container": 27015, "protocol": "tcp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./game/cs2.sh"
