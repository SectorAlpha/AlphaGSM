import gamemodules.kf2server as kf2server
import gamemodules.kfserver as kfserver
import gamemodules.roserver as roserver


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


def test_kfserver_configure_sets_defaults(tmp_path):
    server = DummyServer("kf")

    kfserver.configure(server, ask=False, port=7707, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 215360
    assert server.data["startmap"] == "KF-BioticsLab.rom"


def test_kf2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("kf2")
    exe = tmp_path / "Binaries" / "Win64" / "KFGameSteamServer.bin.x86_64"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Binaries/Win64/KFGameSteamServer.bin.x86_64",
            "startmap": "KF-BioticsLab",
            "gametype": "KFGameContent.KFGameInfo_Survival",
            "port": 7777,
            "queryport": "27015",
        }
    )

    cmd, cwd = kf2server.get_start_command(server)

    assert cmd[0] == "./Binaries/Win64/KFGameSteamServer.bin.x86_64"
    assert "-Port=7777" in cmd
    assert cwd == server.data["dir"]


def test_roserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ro")
    exe = tmp_path / "System" / "ucc-bin"
    exe.parent.mkdir()
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "System/ucc-bin",
            "startmap": "Ostfront-Rakowice",
            "gametype": "ROEngine.ROTeamGame",
            "port": 7757,
            "configfile": "System/RedOrchestra.ini",
        }
    )

    cmd, cwd = roserver.get_start_command(server)

    assert cmd[0] == "./System/ucc-bin"
    assert "-ini=System/RedOrchestra.ini" in cmd
    assert cwd == server.data["dir"]


def test_tripwire_modules_update_downloads_and_optionally_restart(monkeypatch):
    kf = DummyServer("kf")
    kf.data["dir"] = "/srv/kf/"
    kf2 = DummyServer("kf2")
    kf2.data["dir"] = "/srv/kf2/"
    ro = DummyServer("ro")
    ro.data["dir"] = "/srv/ro/"
    calls = []

    monkeypatch.setattr(
        kfserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    kfserver.update(kf, validate=True, restart=True)
    kf2server.update(kf2, validate=False, restart=False)
    roserver.update(ro, validate=False, restart=False)

    assert ("/srv/kf/", 215360, True, True) in calls
    assert ("/srv/kf2/", 232130, True, False) in calls
    assert ("/srv/ro/", 223250, True, False) in calls
    assert kf.start_calls == 1
