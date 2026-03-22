import gamemodules.deadpolyserver as deadpolyserver
import gamemodules.heatserver as heatserver
import gamemodules.longvinterserver as longvinterserver


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


def test_deadpoly_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("deadpoly")
    exe = tmp_path / "DeadPolyServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "DeadPolyServer.sh",
            "port": 7777,
            "queryport": 7779,
            "maxplayers": 100,
        }
    )

    cmd, cwd = deadpolyserver.get_start_command(server)

    assert cmd[0] == "./DeadPolyServer.sh"
    assert "-queryport=7779" in cmd
    assert cwd == server.data["dir"]


def test_heat_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("heat")
    exe = tmp_path / "HeatServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "HeatServer.exe",
            "port": 27015,
            "queryport": 27016,
            "startmap": "America",
            "maxplayers": 32,
        }
    )

    cmd, cwd = heatserver.get_start_command(server)

    assert cmd[0] == "./HeatServer.exe"
    assert "-map" in cmd
    assert cwd == server.data["dir"]


def test_longvinter_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("longvinter")
    exe = tmp_path / "LongvinterServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "LongvinterServer.sh"})

    cmd, cwd = longvinterserver.get_start_command(server)

    assert cmd == ["./LongvinterServer.sh"]
    assert cwd == server.data["dir"]


def test_deadpoly_heat_and_longvinter_update_downloads_and_optionally_restart(monkeypatch):
    deadpoly = DummyServer("deadpoly")
    deadpoly.data["dir"] = "/srv/deadpoly/"
    heat = DummyServer("heat")
    heat.data["dir"] = "/srv/heat/"
    longvinter = DummyServer("longvinter")
    longvinter.data["dir"] = "/srv/longvinter/"
    calls = []

    monkeypatch.setattr(
        deadpolyserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    deadpolyserver.update(deadpoly, validate=True, restart=True)
    heatserver.update(heat, validate=False, restart=False)
    longvinterserver.update(longvinter, validate=False, restart=False)

    assert ("/srv/deadpoly/", 2208380, True, True) in calls
    assert ("/srv/heat/", 996600, True, False) in calls
    assert ("/srv/longvinter/", 1639880, True, False) in calls
    assert deadpoly.start_calls == 1
