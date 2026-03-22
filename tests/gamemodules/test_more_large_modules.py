import gamemodules.jc3server as jc3server
import gamemodules.rwserver as rwserver
import gamemodules.tiserver as tiserver


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


def test_jc3server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("jc3")
    exe = tmp_path / "openjc3-server"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "openjc3-server", "port": 7777, "maxplayers": "64", "gamemode": "freeroam"})

    cmd, cwd = jc3server.get_start_command(server)

    assert cmd == ["./openjc3-server", "--port", "7777", "--players", "64", "--mode", "freeroam"]
    assert cwd == server.data["dir"]


def test_rwserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("rw")
    exe = tmp_path / "server.jar"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "server.jar", "javapath": "java", "world": "rw", "port": 4254})

    cmd, cwd = rwserver.get_start_command(server)

    assert cmd == ["java", "-jar", "server.jar", "--server", "rw", "4254"]
    assert cwd == server.data["dir"]


def test_tiserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ti")
    exe = tmp_path / "TheIsleServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "TheIsleServer.sh", "map": "TheIsle", "port": 7777, "queryport": "7778"})

    cmd, cwd = tiserver.get_start_command(server)

    assert cmd == ["./TheIsleServer.sh", "TheIsle", "-Port=7777", "-QueryPort=7778", "-log"]
    assert cwd == server.data["dir"]


def test_large_modules_update_downloads_and_optionally_restart(monkeypatch):
    jc3 = DummyServer("jc3")
    jc3.data["dir"] = "/srv/jc3/"
    rw = DummyServer("rw")
    rw.data["dir"] = "/srv/rw/"
    ti = DummyServer("ti")
    ti.data["dir"] = "/srv/ti/"
    calls = []

    monkeypatch.setattr(
        jc3server.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    jc3server.update(jc3, validate=True, restart=True)
    rwserver.update(rw, validate=False, restart=False)
    tiserver.update(ti, validate=False, restart=False)

    assert ("/srv/jc3/", 619960, True, True) in calls
    assert ("/srv/rw/", 339010, True, False) in calls
    assert ("/srv/ti/", 412680, True, False) in calls
    assert jc3.start_calls == 1
