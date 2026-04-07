import gamemodules.mw3server as mw3server
import gamemodules.reignofdwarfserver as reignofdwarfserver


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


def test_mw3_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(mw3server.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("mw3")
    exe = tmp_path / "iw5mp_server.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "iw5mp_server.exe",
            "hostname": "AlphaGSM mw3",
            "startmap": "mp_alpha",
            "maxplayers": 18,
            "port": 27016,
        }
    )

    cmd, cwd = mw3server.get_start_command(server)

    assert cmd[0] == "iw5mp_server.exe"
    assert "sv_hostname" in cmd
    assert cwd == server.data["dir"]


def test_reignofdwarf_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(reignofdwarfserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("rod")
    exe = tmp_path / "ReignOfDwarfServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ReignOfDwarfServer.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 16,
        }
    )

    cmd, cwd = reignofdwarfserver.get_start_command(server)

    assert cmd[0] == "ReignOfDwarfServer.exe"
    assert "-queryport" in cmd
    assert cwd == server.data["dir"]


def test_mw3_and_reignofdwarf_update_downloads_and_optionally_restart(monkeypatch):
    mw3 = DummyServer("mw3")
    mw3.data["dir"] = "/srv/mw3/"
    rod = DummyServer("rod")
    rod.data["dir"] = "/srv/rod/"
    calls = []

    monkeypatch.setattr(
        mw3server.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    mw3server.update(mw3, validate=True, restart=True)
    reignofdwarfserver.update(rod, validate=False, restart=False)

    assert ("/srv/mw3/", 115310, False, True) in calls
    assert ("/srv/rod/", 1999160, True, False) in calls
    assert mw3.start_calls == 1
