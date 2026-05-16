import gamemodules.cryofallserver as cryofallserver
import gamemodules.fearthenightserver as fearthenightserver
import gamemodules.frozenflameserver as frozenflameserver


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


def test_cryofall_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("cryo")
    exe = tmp_path / "CryoFall_Server"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "CryoFall_Server"})

    cmd, cwd = cryofallserver.get_start_command(server)

    assert cmd == ["./CryoFall_Server"]
    assert cwd == server.data["dir"]


def test_fearthenight_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        wrap_calls.append(prefer_proton)
        return list(cmd)

    monkeypatch.setattr(fearthenightserver.proton, "wrap_command", fake_wrap_command)
    server = DummyServer("ftn")
    exe_dir = tmp_path / "Moonlight" / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "MoonlightServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Moonlight/Binaries/Win64/MoonlightServer.exe",
            "startmap": "Pittsburgh_Overworld",
        }
    )

    cmd, cwd = fearthenightserver.get_start_command(server)

    assert cmd[0] == "Moonlight/Binaries/Win64/MoonlightServer.exe"
    assert "Pittsburgh_Overworld" in cmd
    assert cwd == server.data["dir"]
    assert wrap_calls == [True]


def test_frozenflame_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ff")
    exe = tmp_path / "FrozenFlameServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "FrozenFlameServer.sh",
                        "port": 7777, "queryport": 27015})

    cmd, cwd = frozenflameserver.get_start_command(server)

    assert cmd == ["./FrozenFlameServer.sh", "-Port=7777", "-QueryPort=27015", "-log"]
    assert cwd == server.data["dir"]


def test_three_updates_download_and_optionally_restart(monkeypatch):
    cryo = DummyServer("cryo")
    cryo.data["dir"] = "/srv/cryo/"
    ftn = DummyServer("ftn")
    ftn.data["dir"] = "/srv/ftn/"
    ff = DummyServer("ff")
    ff.data["dir"] = "/srv/ff/"
    calls = []

    monkeypatch.setattr(
        cryofallserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    cryofallserver.update(cryo, validate=True, restart=True)
    fearthenightserver.update(ftn, validate=False, restart=False)
    frozenflameserver.update(ff, validate=False, restart=False)

    assert ("/srv/cryo/", 1061710, True, True) in calls
    assert ("/srv/ftn/", 764940, True, False) in calls
    assert ("/srv/ff/", 1348640, True, False) in calls
    assert cryo.start_calls == 1
