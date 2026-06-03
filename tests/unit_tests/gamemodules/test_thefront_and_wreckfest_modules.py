import gamemodules.thefrontserver as thefrontserver
import gamemodules.wreckfestserver as wreckfestserver


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


def test_thefrontserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("front")
    exe_dir = tmp_path / "ProjectWar" / "Binaries" / "Linux"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "TheFrontServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ProjectWar/Binaries/Linux/TheFrontServer",
            "port": 7777,
            "queryport": 7779,
            "maxplayers": 32,
            "servername": "AlphaGSM Front",
        }
    )

    cmd, cwd = thefrontserver.get_start_command(server)

    assert cmd[0] == "./ProjectWar/Binaries/Linux/TheFrontServer"
    assert cmd[1] == "ProjectWar"
    assert "ProjectWar_Start?Listen?MaxPlayers=32" in cmd
    assert "-port=7777" in cmd
    assert "-BeaconPort=7778" in cmd
    assert "-QueryPort=7779" in cmd
    assert "-ShutDownServicePort=7780" in cmd
    assert cwd == server.data["dir"]


def test_wreckfestserver_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(
        wreckfestserver.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: list(cmd),
    )
    server = DummyServer("wreck")
    exe = tmp_path / "Wreckfest_x64.exe"
    exe.write_text("")
    (tmp_path / "server_config.cfg").write_text("game_port=33540\n")
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "Wreckfest_x64.exe",
            "configfile": "server_config.cfg",
        }
    )

    cmd, cwd = wreckfestserver.get_start_command(server)

    assert "-s" in cmd
    assert "server_config=server_config.cfg" in cmd
    assert cwd == server.data["dir"]


def test_thefront_and_wreckfest_updates_download_and_optionally_restart(monkeypatch):
    front = DummyServer("front")
    front.data["dir"] = "/srv/front/"
    wreck = DummyServer("wreck")
    wreck.data["dir"] = "/srv/wreck/"
    calls = []

    monkeypatch.setattr(
        thefrontserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, **kwargs: calls.append((path, app_id, anon, validate, kwargs)),
    )

    thefrontserver.update(front, validate=True, restart=True)
    wreckfestserver.update(wreck, validate=False, restart=False)

    assert ("/srv/front/", 2334200, True, True, {}) in calls
    assert ("/srv/wreck/", 361580, True, False, {"force_windows": True}) in calls
    assert front.start_calls == 1
