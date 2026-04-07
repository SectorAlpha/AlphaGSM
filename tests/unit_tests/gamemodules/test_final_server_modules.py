import gamemodules.solserver as solserver
import gamemodules.wurmserver as wurmserver
import gamemodules.xntserver as xntserver


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


def test_solserver_configure_sets_defaults(tmp_path):
    server = DummyServer("soldat")

    solserver.configure(server, ask=False, port=23073, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 638500
    assert server.data["maxplayers"] == "16"


def test_solserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("soldat")
    exe = tmp_path / "soldatserver"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "soldatserver",
            "port": 23073,
            "maxplayers": "16",
        }
    )

    cmd, cwd = solserver.get_start_command(server)

    assert cmd == ["./soldatserver", "-p", "23073", "-maxplayers", "16"]
    assert cwd == server.data["dir"]


def test_wurmserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("wurm")
    exe = tmp_path / "WurmServerLauncher"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "WurmServerLauncher",
            "worldname": "Adventure",
            "port": 3724,
            "queryport": 27016,
            "internalport": 7220,
            "rmiport": 7221,
            "servername": "AlphaGSM wurm",
        }
    )

    cmd, cwd = wurmserver.get_start_command(server)

    assert cmd == [
        "./WurmServerLauncher",
        "start=Adventure",
        "ip=127.0.0.1",
        "externalport=3724",
        "queryport=27016",
        "rmiregport=7220",
        "rmiport=7221",
        "servername=AlphaGSM wurm",
    ]
    assert cwd == server.data["dir"]


def test_xntserver_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("xnt")

    xntserver.configure(
        server,
        ask=False,
        port=26000,
        dir=str(tmp_path),
        url="http://example.com/xonotic.zip",
    )

    assert server.data["gametype"] == "dm"
    assert server.data["download_name"] == "xonotic.zip"


def test_xntserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("xnt")
    exe = tmp_path / "xonotic-linux64-dedicated"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "xonotic-linux64-dedicated",
            "userdir": "server",
            "port": 26000,
            "gametype": "dm",
            "hostname": "AlphaGSM xnt",
        }
    )

    cmd, cwd = xntserver.get_start_command(server)

    assert cmd[0] == "./xonotic-linux64-dedicated"
    assert "+port" in cmd
    assert cwd == server.data["dir"]


def test_sol_and_wurm_update_downloads_and_optionally_restart(monkeypatch):
    sol_server = DummyServer("sol")
    sol_server.data["dir"] = "/srv/sol/"
    wurm_srv = DummyServer("wurm")
    wurm_srv.data["dir"] = "/srv/wurm/"
    calls = []

    monkeypatch.setattr(
        solserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    solserver.update(sol_server, validate=True, restart=True)
    wurmserver.update(wurm_srv, validate=False, restart=False)

    assert ("/srv/sol/", 638500, True, True) in calls
    assert ("/srv/wurm/", 402370, True, False) in calls
    assert sol_server.start_calls == 1
