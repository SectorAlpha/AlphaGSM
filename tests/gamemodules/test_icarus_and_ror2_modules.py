import gamemodules.icarusserver as icarusserver
import gamemodules.ror2server as ror2server


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


def test_icarusserver_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(icarusserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("icarus")
    exe = tmp_path / "IcarusServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "IcarusServer.exe",
            "port": 17777,
            "queryport": 17778,
            "servername": "AlphaGSM icarus",
            "worldname": "icarus",
        }
    )

    cmd, cwd = icarusserver.get_start_command(server)

    assert cmd[0] == "IcarusServer.exe"
    assert "-Port=17777" in cmd
    assert cwd == server.data["dir"]


def test_ror2server_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(ror2server.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("ror2")
    exe = tmp_path / "Risk of Rain 2.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Risk of Rain 2.exe",
            "port": 11100,
            "steamport": 27015,
        }
    )

    cmd, cwd = ror2server.get_start_command(server)

    assert cmd[0] == "Risk of Rain 2.exe"
    assert "+server.port" in cmd
    assert cwd == server.data["dir"]


def test_icarus_and_ror2_updates_download_and_optionally_restart(monkeypatch):
    icarus = DummyServer("icarus")
    icarus.data["dir"] = "/srv/icarus/"
    ror2 = DummyServer("ror2")
    ror2.data["dir"] = "/srv/ror2/"
    calls = []

    monkeypatch.setattr(
        icarusserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    icarusserver.update(icarus, validate=True, restart=True)
    ror2server.update(ror2, validate=False, restart=False)

    assert ("/srv/icarus/", 2089300, True, True) in calls
    assert ("/srv/ror2/", 1180760, True, False) in calls
    assert icarus.start_calls == 1
