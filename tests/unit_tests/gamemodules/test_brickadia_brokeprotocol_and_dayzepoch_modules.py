import gamemodules.brickadiaserver as brickadiaserver
import gamemodules.brokeprotocolserver as brokeprotocolserver
import gamemodules.dayzarma2epochserver as dayzarma2epochserver


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


def test_brickadia_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("brickadia")
    exe = tmp_path / "BrickadiaServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "BrickadiaServer.sh",
            "port": 7777,
            "queryport": 27015,
            "servername": "AlphaGSM brickadia",
        }
    )

    cmd, cwd = brickadiaserver.get_start_command(server)

    assert cmd[0] == "./BrickadiaServer.sh"
    assert "-queryport=27015" in cmd
    assert cwd == server.data["dir"]


def test_brokeprotocol_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bp")
    exe = tmp_path / "Start.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Start.sh",
            "port": 27777,
            "maxplayers": 64,
        }
    )

    cmd, cwd = brokeprotocolserver.get_start_command(server)

    assert cmd[0] == "./Start.sh"
    assert "--maxplayers" in cmd
    assert cwd == server.data["dir"]


def test_dayzepoch_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("epoch")
    exe = tmp_path / "arma2oaserver"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma2oaserver",
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "chernarus",
            "mod": "@DayZ_Epoch",
            "port": 2302,
        }
    )

    cmd, cwd = dayzarma2epochserver.get_start_command(server)

    assert cmd[0] == "./arma2oaserver"
    assert "-mod=@DayZ_Epoch" in cmd
    assert cwd == server.data["dir"]


def test_brickadia_and_brokeprotocol_update_downloads_and_optionally_restart(monkeypatch):
    brickadia = DummyServer("brickadia")
    brickadia.data["dir"] = "/srv/brickadia/"
    broke = DummyServer("bp")
    broke.data["dir"] = "/srv/broke/"
    calls = []

    monkeypatch.setattr(
        brickadiaserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    brickadiaserver.update(brickadia, validate=True, restart=True)
    brokeprotocolserver.update(broke, validate=False, restart=False)

    assert ("/srv/brickadia/", 3017590, False, True) in calls
    assert ("/srv/broke/", 696370, True, False) in calls
    assert brickadia.start_calls == 1
