import gamemodules.avserver as avserver
import gamemodules.boserver as boserver
import gamemodules.btserver as btserver
import gamemodules.btlserver as btlserver


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


def test_avserver_configure_sets_defaults(tmp_path):
    server = DummyServer("avorion")

    avserver.configure(server, ask=False, port=27000, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 565060
    assert server.data["galaxy"] == "avorion"


def test_boserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bo")
    exe = tmp_path / "BODS.x86_64"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "BODS.x86_64", "port": 27015, "map": "oilrig"})

    cmd, cwd = boserver.get_start_command(server)

    assert cmd == ["./BODS.x86_64", "-batchmode", "-nographics", "-port", "27015", "-map", "oilrig"]
    assert cwd == server.data["dir"]


def test_btserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bt")
    exe = tmp_path / "DedicatedServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "DedicatedServer",
            "port": 27015,
            "queryport": "27016",
            "gamemode": "Sandbox",
        }
    )

    cmd, cwd = btserver.get_start_command(server)

    assert cmd == ["./DedicatedServer", "-name", "bt", "-port", "27015", "-queryport", "27016", "-gamemode", "Sandbox"]
    assert cwd == server.data["dir"]


def test_btlserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("btl")
    exe = tmp_path / "Battalion" / "Binaries" / "Linux" / "BattalionServer-Linux-Shipping"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Battalion/Binaries/Linux/BattalionServer-Linux-Shipping",
            "port": 7777,
            "queryport": "7788",
            "map": "Derailed",
        }
    )

    cmd, cwd = btlserver.get_start_command(server)

    assert cmd == [
        "./Battalion/Binaries/Linux/BattalionServer-Linux-Shipping",
        "Derailed",
        "-Port=7777",
        "-QueryPort=7788",
        "-log",
    ]
    assert cwd == server.data["dir"]


def test_modules_update_downloads_and_optional_restart(monkeypatch):
    av = DummyServer("av")
    av.data["dir"] = "/srv/av/"
    bo = DummyServer("bo")
    bo.data["dir"] = "/srv/bo/"
    bt = DummyServer("bt")
    bt.data["dir"] = "/srv/bt/"
    calls = []

    monkeypatch.setattr(
        avserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    avserver.update(av, validate=True, restart=True)
    boserver.update(bo, validate=False, restart=False)
    btserver.update(bt, validate=False, restart=False)

    assert ("/srv/av/", 565060, True, True) in calls
    assert ("/srv/bo/", 416881, True, False) in calls
    assert ("/srv/bt/", 1026340, True, False) in calls
    assert av.start_calls == 1
