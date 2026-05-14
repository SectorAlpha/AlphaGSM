import gamemodules.bannerlordserver as bannerlordserver
import gamemodules.readyornotserver as readyornotserver


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


def test_bannerlord_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("banner")
    exe = tmp_path / "Bannerlord.DedicatedServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Bannerlord.DedicatedServer",
            "port": 7210,
            "queryport": 7211,
            "game_type": "Captain",
            "scene": "mp_sergeant_battle",
            "maxplayers": 64,
        }
    )

    cmd, cwd = bannerlordserver.get_start_command(server)

    assert cmd[0] == "./Bannerlord.DedicatedServer"
    assert "_PORT_7210" in cmd
    assert "_QUERYPORT_7211" in cmd
    assert cwd == server.data["dir"]


def test_readyornot_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    observed = {}

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        observed["wineprefix"] = wineprefix
        observed["prefer_proton"] = prefer_proton
        return list(cmd)

    monkeypatch.setattr(readyornotserver.proton, "wrap_command", fake_wrap_command)
    monkeypatch.setattr(readyornotserver, "IS_LINUX", True)
    server = DummyServer("ron")
    exe = tmp_path / "ReadyOrNotServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ReadyOrNotServer.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 16,
        }
    )

    cmd, cwd = readyornotserver.get_start_command(server)

    assert cmd[0] == "ReadyOrNotServer.exe"
    assert "-Port=7777" in cmd
    assert "-QueryPort=27015" in cmd
    assert cwd == server.data["dir"]
    assert observed == {"wineprefix": None, "prefer_proton": False}


def test_bannerlord_and_readyornot_update_downloads_and_optionally_restart(monkeypatch):
    banner = DummyServer("banner")
    banner.data["dir"] = "/srv/banner/"
    ron = DummyServer("ron")
    ron.data["dir"] = "/srv/ron/"
    calls = []

    monkeypatch.setattr(
        bannerlordserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    bannerlordserver.update(banner, validate=True, restart=True)
    readyornotserver.update(ron, validate=False, restart=False)

    assert ("/srv/banner/", 1863440, True, True) in calls
    assert ("/srv/ron/", 950290, True, False) in calls
    assert banner.start_calls == 1
