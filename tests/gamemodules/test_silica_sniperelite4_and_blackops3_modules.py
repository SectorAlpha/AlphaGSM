import gamemodules.blackops3server as blackops3server
import gamemodules.silicaserver as silicaserver
import gamemodules.sniperelite4server as sniperelite4server


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


def test_silica_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("silica")
    exe = tmp_path / "Silica.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Silica.x86_64",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 64,
        }
    )

    cmd, cwd = silicaserver.get_start_command(server)

    assert cmd[0] == "./Silica.x86_64"
    assert "-queryport" in cmd
    assert cwd == server.data["dir"]


def test_sniperelite4_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("se4")
    exe = tmp_path / "SniperElite4_DedicatedServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "SniperElite4_DedicatedServer.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 12,
        }
    )

    cmd, cwd = sniperelite4server.get_start_command(server)

    assert cmd[0] == "./SniperElite4_DedicatedServer.exe"
    assert "-queryport" in cmd
    assert cwd == server.data["dir"]


def test_blackops3_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bo3")
    exe = tmp_path / "BlackOps3Server.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "BlackOps3Server.exe",
            "port": 28960,
            "maxplayers": 18,
        }
    )

    cmd, cwd = blackops3server.get_start_command(server)

    assert cmd[0] == "./BlackOps3Server.exe"
    assert "sv_maxclients" in cmd
    assert cwd == server.data["dir"]


def test_silica_and_blackops3_update_downloads_and_optionally_restart(monkeypatch):
    silica = DummyServer("silica")
    silica.data["dir"] = "/srv/silica/"
    bo3 = DummyServer("bo3")
    bo3.data["dir"] = "/srv/bo3/"
    calls = []

    monkeypatch.setattr(
        silicaserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    silicaserver.update(silica, validate=True, restart=True)
    blackops3server.update(bo3, validate=False, restart=False)

    assert ("/srv/silica/", 2738040, True, True) in calls
    assert ("/srv/bo3/", 545990, True, False) in calls
    assert silica.start_calls == 1
