import gamemodules.notdserver as notdserver
import gamemodules.soulmask as soulmask
import gamemodules.stnserver as stnserver


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


def test_soulmask_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("soul")
    exe = tmp_path / "WSServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "WSServer.sh",
            "level": "Level01_Main",
            "servername": "AlphaGSM soul",
            "maxplayers": 10,
            "serverpassword": "",
            "adminpassword": "alphagsm",
            "bindaddress": "0.0.0.0",
            "port": 8777,
            "queryport": 27015,
            "echoport": 18888,
            "savinginterval": 600,
            "backupinterval": 900,
            "mods": "",
        }
    )

    cmd, cwd = soulmask.get_start_command(server)

    assert cmd[0] == "./WSServer.sh"
    assert "-Port=8777" in cmd
    assert "-QueryPort=27015" in cmd
    assert cwd == server.data["dir"]


def test_stnserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("stn")
    exe = tmp_path / "Server_Linux_x64"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "Server_Linux_x64"})

    cmd, cwd = stnserver.get_start_command(server)

    assert cmd == ["./Server_Linux_x64"]
    assert cwd == server.data["dir"]


def test_notdserver_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(notdserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("notd")
    exe_dir = tmp_path / "LF" / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "LFServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "LF/Binaries/Win64/LFServer.exe",
            "port": 7777,
            "queryport": 27015,
        }
    )

    cmd, cwd = notdserver.get_start_command(server)

    assert cmd == [
        "LF/Binaries/Win64/LFServer.exe",
        "?listen",
        "-log",
        "-Port=7777",
        "-QueryPort=27015",
    ]
    assert cwd == server.data["dir"]


def test_more_survival_modules_update_downloads_and_optionally_restart(monkeypatch):
    soul = DummyServer("soul")
    soul.data["dir"] = "/srv/soul/"
    stn = DummyServer("stn")
    stn.data["dir"] = "/srv/stn/"
    notd = DummyServer("notd")
    notd.data["dir"] = "/srv/notd/"
    calls = []

    monkeypatch.setattr(
        soulmask.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    soulmask.update(soul, validate=True, restart=True)
    stnserver.update(stn, validate=False, restart=False)
    notdserver.update(notd, validate=False, restart=False)

    assert ("/srv/soul/", 3017300, True, True) in calls
    assert ("/srv/stn/", 1502300, True, False) in calls
    assert ("/srv/notd/", 1420710, True, False) in calls
    assert soul.start_calls == 1
