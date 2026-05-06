import gamemodules.chivalryserver as chivalryserver
import gamemodules.exfilserver as exfilserver
import gamemodules.hellletlooseserver as hellletlooseserver


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


def test_exfil_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("exfil")
    exe = tmp_path / "ExfilServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ExfilServer.sh",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 32,
        }
    )

    cmd, cwd = exfilserver.get_start_command(server)

    assert cmd[0] == "./ExfilServer.sh"
    assert "-QueryPort=27015" in cmd
    assert cwd == server.data["dir"]


def test_hellletloose_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(hellletlooseserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("hll")
    exe = tmp_path / "HLLServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "HLLServer.exe",
            "startmap": "/Game/Maps/hurtgenforest_warfare",
        }
    )

    cmd, cwd = hellletlooseserver.get_start_command(server)

    assert cmd == ["HLLServer.exe", "/Game/Maps/hurtgenforest_warfare", "-log"]
    assert cwd == server.data["dir"]


def test_chivalry_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("chiv")
    exe_dir = tmp_path / "Binaries" / "Linux"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "UDKGameServer-Linux"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Binaries/Linux/UDKGameServer-Linux",
            "startmap": "AOCTO-Battlegrounds_V3_P",
            "port": 7777,
        }
    )

    cmd, cwd = chivalryserver.get_start_command(server)

    assert cmd[0] == "./Binaries/Linux/UDKGameServer-Linux"
    assert "AOCTO-Battlegrounds_V3_P?Port=7777?steamsockets" in cmd
    assert cwd == server.data["dir"]


def test_exfil_and_hll_update_downloads_and_optionally_restart(monkeypatch):
    exfil = DummyServer("exfil")
    exfil.data["dir"] = "/srv/exfil/"
    hll = DummyServer("hll")
    hll.data["dir"] = "/srv/hll/"
    calls = []

    monkeypatch.setattr(
        exfilserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    exfilserver.update(exfil, validate=True, restart=True)
    hellletlooseserver.update(hll, validate=False, restart=False)

    assert ("/srv/exfil/", 3093190, True, True) in calls
    assert ("/srv/hll/", 822500, False, False) in calls
    assert exfil.start_calls == 1
