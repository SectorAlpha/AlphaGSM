import gamemodules.motortownserver as motortownserver
import gamemodules.noonesurvivedserver as noonesurvivedserver
import gamemodules.subsistenceserver as subsistenceserver


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


def test_motortown_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(motortownserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("mt")
    exe_dir = tmp_path / "MotorTown" / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "MotorTownServer-Win64-Shipping.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "MotorTown/Binaries/Win64/MotorTownServer-Win64-Shipping.exe",
            "startmap": "Jeju_World",
            "port": 7777,
            "queryport": 27015,
        }
    )

    cmd, cwd = motortownserver.get_start_command(server)

    assert cmd[0] == "MotorTown/Binaries/Win64/MotorTownServer-Win64-Shipping.exe"
    assert "-useperfthreads" in cmd
    assert cwd == server.data["dir"]


def test_noonesurvived_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(noonesurvivedserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("nos")
    exe = tmp_path / "WRSHServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "WRSHServer.exe",
            "port": 7777,
            "queryport": 27015,
            "servername": "AlphaGSM nos",
        }
    )

    cmd, cwd = noonesurvivedserver.get_start_command(server)

    assert cmd[0] == "WRSHServer.exe"
    assert "-servername=AlphaGSM nos" in cmd
    assert cwd == server.data["dir"]


def test_subsistence_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(subsistenceserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    monkeypatch.setattr(subsistenceserver, "IS_LINUX", False)
    server = DummyServer("subs")
    exe_dir = tmp_path / "Binaries" / "Win32"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "Subsistence.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Binaries/Win32/Subsistence.exe",
            "port": 27015,
            "queryport": 27016,
            "maxplayers": 10,
        }
    )
    import os

    cmd, cwd = subsistenceserver.get_start_command(server)

    assert cmd == ["Subsistence.exe", "server coldmap1?Port=27015?QueryPort=27016?MaxPlayers=10?steamsockets", "-log"]
    assert cwd == os.path.join(server.data["dir"], "Binaries", "Win32")


def test_motortown_noonesurvived_and_subsistence_update_downloads_and_optionally_restart(monkeypatch):
    motortown = DummyServer("mt")
    motortown.data["dir"] = "/srv/mt/"
    nos = DummyServer("nos")
    nos.data["dir"] = "/srv/nos/"
    subs = DummyServer("subs")
    subs.data["dir"] = "/srv/subs/"
    calls = []

    monkeypatch.setattr(
        motortownserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    motortownserver.update(motortown, validate=True, restart=True)
    noonesurvivedserver.update(nos, validate=False, restart=False)
    subsistenceserver.update(subs, validate=False, restart=False)

    assert ("/srv/mt/", 2223650, False, True) in calls
    assert ("/srv/nos/", 2329680, True, False) in calls
    assert ("/srv/subs/", 1362640, True, False) in calls
    assert motortown.start_calls == 1
