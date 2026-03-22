import gamemodules.battlebitserver as battlebitserver
import gamemodules.citadelserver as citadelserver
import gamemodules.staxelserver as staxelserver


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


def test_citadel_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("citadel")
    exe = tmp_path / "CitadelServer-Linux-Shipping"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "CitadelServer-Linux-Shipping",
            "map": "rook",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 50,
            "servername": "AlphaGSM citadel",
        }
    )

    cmd, cwd = citadelserver.get_start_command(server)

    assert cmd[0] == "./CitadelServer-Linux-Shipping"
    assert "-ServerName=AlphaGSM citadel" in cmd
    assert cwd == server.data["dir"]


def test_battlebit_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bb")
    exe = tmp_path / "BattleBitDedicatedServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "BattleBitDedicatedServer",
            "port": 7787,
            "queryport": 27015,
            "maxplayers": 127,
        }
    )

    cmd, cwd = battlebitserver.get_start_command(server)

    assert cmd[0] == "./BattleBitDedicatedServer"
    assert "-queryport" in cmd
    assert cwd == server.data["dir"]


def test_staxel_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("staxel")
    exe_dir = tmp_path / "bin"
    exe_dir.mkdir()
    exe = exe_dir / "Staxel.ServerWizard.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "bin/Staxel.ServerWizard.exe",
        }
    )

    cmd, cwd = staxelserver.get_start_command(server)

    assert cmd == ["./bin/Staxel.ServerWizard.exe"]
    assert cwd == server.data["dir"]


def test_citadel_and_battlebit_update_downloads_and_optionally_restart(monkeypatch):
    citadel = DummyServer("citadel")
    citadel.data["dir"] = "/srv/citadel/"
    battlebit = DummyServer("bb")
    battlebit.data["dir"] = "/srv/battlebit/"
    calls = []

    monkeypatch.setattr(
        citadelserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    citadelserver.update(citadel, validate=True, restart=True)
    battlebitserver.update(battlebit, validate=False, restart=False)

    assert ("/srv/citadel/", 489650, True, True) in calls
    assert ("/srv/battlebit/", 689410, True, False) in calls
    assert citadel.start_calls == 1
