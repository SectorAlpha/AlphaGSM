import gamemodules.colserver as colserver
import gamemodules.hzserver as hzserver
import gamemodules.ohdserver as ohdserver


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


def test_colserver_configure_sets_defaults(tmp_path):
    server = DummyServer("col")

    colserver.configure(server, ask=False, port=27004, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 748090
    assert server.data["world"] == "col"


def test_hzserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("hz")
    exe = tmp_path / "HumanitZServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "HumanitZServer.sh", "map": "Main", "port": 7777, "queryport": "27016"})

    cmd, cwd = hzserver.get_start_command(server)

    assert cmd == ["./HumanitZServer.sh", "Main", "-Port=7777", "-QueryPort=27016"]
    assert cwd == server.data["dir"]


def test_ohdserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ohd")
    exe = tmp_path / "OHDServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "OHDServer.sh", "map": "FOB_Anvil", "port": 7777, "queryport": "27015"})

    cmd, cwd = ohdserver.get_start_command(server)

    assert cmd == ["./OHDServer.sh", "FOB_Anvil", "-Port=7777", "-QueryPort=27015", "-log"]
    assert cwd == server.data["dir"]


def test_tail_modules_update_downloads_and_optionally_restart(monkeypatch):
    col = DummyServer("col")
    col.data["dir"] = "/srv/col/"
    hz = DummyServer("hz")
    hz.data["dir"] = "/srv/hz/"
    ohd = DummyServer("ohd")
    ohd.data["dir"] = "/srv/ohd/"
    calls = []

    monkeypatch.setattr(
        colserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    colserver.update(col, validate=True, restart=True)
    hzserver.update(hz, validate=False, restart=False)
    ohdserver.update(ohd, validate=False, restart=False)

    assert ("/srv/col/", 748090, True, True) in calls
    assert ("/srv/hz/", 2728330, True, False) in calls
    assert ("/srv/ohd/", 950900, True, False) in calls
    assert col.start_calls == 1
