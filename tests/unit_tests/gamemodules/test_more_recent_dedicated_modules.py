from unittest.mock import patch

import gamemodules.abfserver as abfserver
import gamemodules.seserver as seserver
import gamemodules.vrserver as vrserver


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


def test_abfserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("abf")
    exe = tmp_path / "AbioticFactorServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "AbioticFactorServer.sh", "world": "abf", "port": 7777, "queryport": "27016"})

    cmd, cwd = abfserver.get_start_command(server)

    assert cmd == ["./AbioticFactorServer.sh", "abf", "-Port=7777", "-QueryPort=27016"]
    assert cwd == server.data["dir"]


def test_vrserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("vr")
    exe = tmp_path / "VRisingServer.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "VRisingServer.exe", "port": 9876, "queryport": "27016"})

    with patch.object(
        vrserver.proton,
        "wrap_command",
        side_effect=lambda command, **_kwargs: command,
    ):
        cmd, cwd = vrserver.get_start_command(server)

    assert cmd == ["VRisingServer.exe", "-persistentDataPath", str(tmp_path / "save-data"), "-serverPort", "9876", "-queryPort", "27016"]
    assert cwd == server.data["dir"]


def test_seserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("se")
    exe = tmp_path / "DedicatedServer64" / "SpaceEngineersDedicated.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "DedicatedServer64/SpaceEngineersDedicated.exe",
            "port": 27015,
        }
    )

    with patch.object(seserver, "IS_LINUX", False):
        cmd, cwd = seserver.get_start_command(server)

    assert cmd == [
        "SpaceEngineersDedicated.exe",
        "-console",
        "-path",
        str(tmp_path),
        "-port",
        "27015",
        "-start",
    ]
    assert cwd == str(tmp_path / "DedicatedServer64")


def test_recent_modules_update_downloads_and_optionally_restart(monkeypatch):
    abf = DummyServer("abf")
    abf.data["dir"] = "/srv/abf/"
    vr = DummyServer("vr")
    vr.data["dir"] = "/srv/vr/"
    se = DummyServer("se")
    se.data["dir"] = "/srv/se/"
    calls = []

    monkeypatch.setattr(
        abfserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, **kwargs: calls.append(
            (path, app_id, anon, validate, kwargs)
        ),
    )

    abfserver.update(abf, validate=True, restart=True)
    vrserver.update(vr, validate=False, restart=False)
    seserver.update(se, validate=False, restart=False)

    assert ("/srv/abf/", 2857200, True, True, {}) in calls
    assert ("/srv/vr/", 1829350, True, False, {}) in calls
    assert ("/srv/se/", 298740, True, False, {"force_windows": True}) in calls
    assert abf.start_calls == 1
