import gamemodules.hurtworldserver as hurtworldserver
import gamemodules.lastoasisserver as lastoasisserver
import gamemodules.miscreatedserver as miscreatedserver


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


def test_hurtworld_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("hurt")
    exe = tmp_path / "HurtworldDedicated"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "HurtworldDedicated",
            "port": 12871,
            "queryport": 12872,
            "worldname": "hurtworld",
            "maxplayers": 50,
        }
    )

    cmd, cwd = hurtworldserver.get_start_command(server)

    assert cmd[0] == "./HurtworldDedicated"
    assert "-worldname" in cmd
    assert cwd == server.data["dir"]


def test_lastoasis_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("oasis")
    exe = tmp_path / "LastOasisServer.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "LastOasisServer.x86_64",
            "port": 15000,
            "queryport": 15001,
            "worldname": "oasisworld",
            "maxplayers": 100,
        }
    )

    cmd, cwd = lastoasisserver.get_start_command(server)

    assert cmd[0] == "./LastOasisServer.x86_64"
    assert "-worldname=oasisworld" in cmd
    assert cwd == server.data["dir"]


def test_miscreated_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(miscreatedserver.proton, "wrap_command", lambda cmd, wineprefix=None, prefer_proton=False: list(cmd))
    server = DummyServer("mis")
    exe_dir = tmp_path / "Bin64_dedicated"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "MiscreatedServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Bin64_dedicated/MiscreatedServer.exe",
            "port": 64090,
            "maxplayers": 50,
            "startmap": "islands",
            "gameserverid": "100",
            "servername": "AlphaGSM mis",
        }
    )

    cmd, cwd = miscreatedserver.get_start_command(server)

    assert cmd[0] == "Bin64_dedicated/MiscreatedServer.exe"
    assert "+sv_servername" in cmd
    assert cwd == server.data["dir"]


def test_hurtworld_lastoasis_and_miscreated_update_downloads_and_optionally_restart(monkeypatch):
    hurt = DummyServer("hurt")
    hurt.data["dir"] = "/srv/hurt/"
    oasis = DummyServer("oasis")
    oasis.data["dir"] = "/srv/oasis/"
    mis = DummyServer("mis")
    mis.data["dir"] = "/srv/mis/"
    calls = []

    monkeypatch.setattr(
        hurtworldserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    hurtworldserver.update(hurt, validate=True, restart=True)
    lastoasisserver.update(oasis, validate=False, restart=False)
    miscreatedserver.update(mis, validate=False, restart=False)

    assert ("/srv/hurt/", 405100, True, True) in calls
    assert ("/srv/oasis/", 920720, True, False) in calls
    assert ("/srv/mis/", 302200, True, False) in calls
    assert hurt.start_calls == 1
