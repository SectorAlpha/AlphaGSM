import gamemodules.blackwakeserver as blackwakeserver
import gamemodules.goldeneyesourceserver as goldeneyesourceserver
import gamemodules.police1013server as police1013server


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


def test_blackwake_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(blackwakeserver.proton, "wrap_command", lambda cmd, wineprefix=None, prefer_proton=False: list(cmd))
    server = DummyServer("bw")
    exe = tmp_path / "Blackwake Dedicated Server.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Blackwake Dedicated Server.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 54,
        }
    )

    cmd, cwd = blackwakeserver.get_start_command(server)

    assert cmd[0] == "Blackwake Dedicated Server.exe"
    assert "-queryport" in cmd
    assert cwd == server.data["dir"]


def test_police1013_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("p1013")
    exe = tmp_path / "RPCityServer.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "RPCityServer.x86_64",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 64,
        }
    )

    cmd, cwd = police1013server.get_start_command(server)

    assert cmd[0] == "./RPCityServer.x86_64"
    assert "-maxplayers" in cmd
    assert cwd == server.data["dir"]


def test_goldeneyesource_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ges")
    exe = tmp_path / "srcds_run"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "srcds_run",
            "game": "gesource",
            "startmap": "ge_archives",
            "maxplayers": 16,
            "port": 27015,
        }
    )

    cmd, cwd = goldeneyesourceserver.get_start_command(server)

    assert cmd[0] == "./srcds_run"
    assert "gesource" in cmd
    assert cwd == server.data["dir"]


def test_blackwake_and_police1013_update_downloads_and_optionally_restart(monkeypatch):
    blackwake = DummyServer("bw")
    blackwake.data["dir"] = "/srv/blackwake/"
    police = DummyServer("p1013")
    police.data["dir"] = "/srv/police1013/"
    calls = []

    monkeypatch.setattr(
        blackwakeserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    blackwakeserver.update(blackwake, validate=True, restart=True)
    police1013server.update(police, validate=False, restart=False)

    assert ("/srv/blackwake/", 423410, True, True) in calls
    assert ("/srv/police1013/", 2691380, True, False) in calls
    assert blackwake.start_calls == 1
