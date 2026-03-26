import gamemodules.rs2server as rs2server
import gamemodules.scumserver as scumserver


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


def test_scumserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("scum")
    exe_dir = tmp_path / "SCUM" / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "SCUMServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "SCUM/Binaries/Win64/SCUMServer.exe",
            "port": 7777,
            "queryport": 7779,
            "maxplayers": 64,
        }
    )

    cmd, cwd = scumserver.get_start_command(server)

    assert cmd[0] == "./SCUM/Binaries/Win64/SCUMServer.exe"
    assert "-port=7777" in cmd
    assert cwd == server.data["dir"]


def test_rs2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("rs2")
    exe_dir = tmp_path / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "VNGame.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Binaries/Win64/VNGame.exe",
            "port": 7777,
            "queryport": 27015,
        }
    )

    cmd, cwd = rs2server.get_start_command(server)

    assert cmd[0] == "./Binaries/Win64/VNGame.exe"
    assert "-Port=7777" in cmd
    assert cwd == server.data["dir"]


def test_scum_and_rs2_updates_download_and_optionally_restart(monkeypatch):
    scum = DummyServer("scum")
    scum.data["dir"] = "/srv/scum/"
    rs2 = DummyServer("rs2")
    rs2.data["dir"] = "/srv/rs2/"
    calls = []

    monkeypatch.setattr(
        scumserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    scumserver.update(scum, validate=True, restart=True)
    rs2server.update(rs2, validate=False, restart=False)

    assert ("/srv/scum/", 3792580, True, True) in calls
    assert ("/srv/rs2/", 418480, True, False) in calls
    assert scum.start_calls == 1
