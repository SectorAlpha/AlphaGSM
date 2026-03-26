import gamemodules.outpostzeroserver as outpostzeroserver
import gamemodules.pixarkserver as pixarkserver
import gamemodules.reignofkingsserver as reignofkingsserver


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


def test_pixark_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("pixark")
    exe = tmp_path / "PixARKServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "PixARKServer.exe",
            "map": "CubeWorld_Light",
            "port": 27015,
            "queryport": 27016,
            "maxplayers": 70,
        }
    )

    cmd, cwd = pixarkserver.get_start_command(server)

    assert cmd[0] == "./PixARKServer.exe"
    assert "-QueryPort=27016" in cmd
    assert cwd == server.data["dir"]


def test_outpostzero_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("opz")
    exe = tmp_path / "OutpostZeroServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "OutpostZeroServer.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 16,
            "servername": "AlphaGSM opz",
        }
    )

    cmd, cwd = outpostzeroserver.get_start_command(server)

    assert cmd[0] == "./OutpostZeroServer.exe"
    assert "-ServerName=AlphaGSM opz" in cmd
    assert cwd == server.data["dir"]


def test_reignofkings_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("rok")
    exe = tmp_path / "Server.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Server.exe",
            "port": 25147,
            "queryport": 27015,
            "maxplayers": 40,
            "worldname": "rokworld",
        }
    )

    cmd, cwd = reignofkingsserver.get_start_command(server)

    assert cmd[0] == "./Server.exe"
    assert "-worldname" in cmd
    assert "rokworld" in cmd
    assert cwd == server.data["dir"]


def test_pixark_outpostzero_and_reignofkings_update_downloads_and_optionally_restart(monkeypatch):
    pixark = DummyServer("pixark")
    pixark.data["dir"] = "/srv/pixark/"
    opz = DummyServer("opz")
    opz.data["dir"] = "/srv/opz/"
    rok = DummyServer("rok")
    rok.data["dir"] = "/srv/rok/"
    calls = []

    monkeypatch.setattr(
        pixarkserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    pixarkserver.update(pixark, validate=True, restart=True)
    outpostzeroserver.update(opz, validate=False, restart=False)
    reignofkingsserver.update(rok, validate=False, restart=False)

    assert ("/srv/pixark/", 824360, True, True) in calls
    assert ("/srv/opz/", 762880, True, False) in calls
    assert ("/srv/rok/", 381690, True, False) in calls
    assert pixark.start_calls == 1
