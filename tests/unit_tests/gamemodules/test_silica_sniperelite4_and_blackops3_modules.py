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

    assert cmd == ["env", f"HOME={tmp_path}/.alphagsm-home", "./Silica.x86_64",
                   "-batchmode", "-nographics"]
    assert cwd == server.data["dir"]


def test_sniperelite4_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        wrap_calls.append(prefer_proton)
        return list(cmd)

    monkeypatch.setattr(sniperelite4server.proton, "wrap_command", fake_wrap_command)
    monkeypatch.setattr(sniperelite4server.shutil, "which", lambda _name: None)
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

    assert cmd == [
        "SniperElite4_DedicatedServer.exe",
        "exec",
        "default.cfg",
    ]
    assert cwd == server.data["dir"]
    assert wrap_calls == [True]


def test_blackops3_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(blackops3server.proton, "wrap_command", lambda cmd, wineprefix=None, prefer_proton=False: list(cmd))
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

    assert cmd[0] == "BlackOps3_UnrankedDedicatedServer.exe"
    assert "sv_maxclients" in cmd
    import os
    assert cwd == os.path.join(server.data["dir"], "UnrankedServer")


def test_sniperelite4_runtime_metadata_prefers_proton(tmp_path):
    server = DummyServer("sniper")
    (tmp_path / "SniperElite4_DedicatedServer.exe").write_text("")
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "SniperElite4_DedicatedServer.exe",
            "port": 7777,
        }
    )

    requirements = sniperelite4server.get_runtime_requirements(server)
    spec = sniperelite4server.get_container_spec(server)

    assert requirements["env"]["ALPHAGSM_PREFER_PROTON"] == "1"
    assert spec["env"]["ALPHAGSM_PREFER_PROTON"] == "1"


def test_silica_and_blackops3_update_downloads_and_optionally_restart(monkeypatch):
    silica = DummyServer("silica")
    silica.data["dir"] = "/srv/silica/"
    bo3 = DummyServer("bo3")
    bo3.data["dir"] = "/srv/bo3/"
    calls = []

    monkeypatch.setattr(
        silicaserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    silicaserver.update(silica, validate=True, restart=True)
    blackops3server.update(bo3, validate=False, restart=False)

    assert ("/srv/silica/", 2738040, True, True) in calls
    assert ("/srv/bo3/", 545990, True, False) in calls
    assert silica.start_calls == 1
