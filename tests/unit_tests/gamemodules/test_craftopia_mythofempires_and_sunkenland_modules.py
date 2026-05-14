import gamemodules.craftopiaserver as craftopiaserver
import gamemodules.mythofempiresserver as mythofempiresserver
import gamemodules.sunkenlandserver as sunkenlandserver


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


def test_craftopia_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("craft")
    exe = tmp_path / "Craftopia.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Craftopia.x86_64",
            "port": 8787,
            "queryport": 27015,
            "worldname": "craftworld",
        }
    )

    cmd, cwd = craftopiaserver.get_start_command(server)

    assert cmd == ["./Craftopia.x86_64", "-batchmode", "-nographics"]
    assert cwd == server.data["dir"]


def test_mythofempires_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(mythofempiresserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("moe")
    exe_dir = tmp_path / "MOE" / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "MOEServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "MOE/Binaries/Win64/MOEServer.exe",
            "port": 12888,
            "queryport": 27015,
            "maxplayers": 100,
            "servername": "AlphaGSM moe",
        }
    )

    cmd, cwd = mythofempiresserver.get_start_command(server)

    assert cmd[0] == "MOE/Binaries/Win64/MOEServer.exe"
    assert "-ServerName=AlphaGSM moe" in cmd
    assert cwd == server.data["dir"]


def test_sunkenland_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        wrap_calls.append(prefer_proton)
        return list(cmd)

    monkeypatch.setattr(sunkenlandserver.proton, "wrap_command", fake_wrap_command)
    server = DummyServer("sunken")
    exe = tmp_path / "Sunkenland-DedicatedServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Sunkenland-DedicatedServer.exe",
            "port": 29000,
            "queryport": 27015,
            "servername": "AlphaGSM sunken",
        }
    )

    cmd, cwd = sunkenlandserver.get_start_command(server)

    assert cmd[0] == "Sunkenland-DedicatedServer.exe"
    assert "-servername" in cmd
    assert cwd == server.data["dir"]
    assert wrap_calls == [True]


def test_craftopia_mythofempires_and_sunkenland_update_downloads_and_optionally_restart(monkeypatch):
    craft = DummyServer("craft")
    craft.data["dir"] = "/srv/craft/"
    moe = DummyServer("moe")
    moe.data["dir"] = "/srv/moe/"
    sunken = DummyServer("sunken")
    sunken.data["dir"] = "/srv/sunken/"
    calls = []

    monkeypatch.setattr(
        craftopiaserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    craftopiaserver.update(craft, validate=True, restart=True)
    mythofempiresserver.update(moe, validate=False, restart=False)
    sunkenlandserver.update(sunken, validate=False, restart=False)

    assert ("/srv/craft/", 1670340, True, True) in calls
    assert ("/srv/moe/", 1794810, True, False) in calls
    assert ("/srv/sunken/", 2667530, True, False) in calls
    assert craft.start_calls == 1
