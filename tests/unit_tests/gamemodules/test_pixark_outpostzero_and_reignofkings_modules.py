import gamemodules.outpostzeroserver as outpostzeroserver
import gamemodules.pixarkserver as pixarkserver
import gamemodules.reignofkingsserver as reignofkingsserver


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


def test_pixark_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(pixarkserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("pixark")
    exe = tmp_path / "PixARKServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "PixARKServer.exe",
            "map": "CubeWorld_Light",
            "port": 27015,
            "queryport": 27016,
            "maxplayers": 70,
        }
    )

    cmd, cwd = pixarkserver.get_start_command(server)

    assert cmd[0] == "PixARKServer.exe"
    assert "-QueryPort=27016" in cmd
    assert cwd == server.data["dir"]


def test_outpostzero_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(outpostzeroserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("opz")
    exe = tmp_path / "OutpostZeroServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "OutpostZeroServer.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 16,
            "servername": "AlphaGSM opz",
        }
    )

    cmd, cwd = outpostzeroserver.get_start_command(server)

    assert cmd[0] == "OutpostZeroServer.exe"
    assert "-ServerName=AlphaGSM opz" in cmd
    assert cwd == server.data["dir"]


def test_outpostzero_runtime_requirements_use_wine_proton_family(tmp_path, monkeypatch):
    monkeypatch.setattr(outpostzeroserver, "IS_LINUX", True)
    monkeypatch.setattr(
        outpostzeroserver.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "/usr/bin/wine",
        ]
        + list(cmd),
    )
    server = DummyServer("opz")
    exe = tmp_path / "WindowsServer" / "SurvivalGameServer.exe"
    exe.parent.mkdir()
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "WindowsServer/SurvivalGameServer.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 16,
            "servername": "AlphaGSM opz",
        }
    )

    requirements = outpostzeroserver.get_runtime_requirements(server)
    spec = outpostzeroserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "wine-proton"
    assert requirements["ports"] == [
        {"host": 7777, "container": 7777, "protocol": "udp"},
        {"host": 27015, "container": 27015, "protocol": "udp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "WindowsServer/SurvivalGameServer.exe"


def test_reignofkings_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        wrap_calls.append(prefer_proton)
        return list(cmd)

    monkeypatch.setattr(reignofkingsserver.proton, "wrap_command", fake_wrap_command)
    server = DummyServer("rok")
    exe = tmp_path / "Server.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Server.exe",
            "port": 25147,
            "queryport": 27015,
            "maxplayers": 40,
            "worldname": "rokworld",
        }
    )

    cmd, cwd = reignofkingsserver.get_start_command(server)

    assert cmd[0] == "Server.exe"
    assert "-worldname" in cmd
    assert "rokworld" in cmd
    assert cwd == server.data["dir"]
    assert wrap_calls == [True]


def test_pixark_outpostzero_and_reignofkings_update_downloads_and_optionally_restart(monkeypatch):
    pixark = DummyServer("pixark")
    pixark.data["dir"] = "/srv/pixark/"
    opz = DummyServer("opz")
    opz.data["dir"] = "/srv/opz/"
    rok = DummyServer("rok")
    rok.data["dir"] = "/srv/rok/"
    calls = []

    monkeypatch.setattr(
        pixarkserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    pixarkserver.update(pixark, validate=True, restart=True)
    outpostzeroserver.update(opz, validate=False, restart=False)
    reignofkingsserver.update(rok, validate=False, restart=False)

    assert ("/srv/pixark/", 824360, True, True) in calls
    assert ("/srv/opz/", 762880, True, False) in calls
    assert ("/srv/rok/", 381690, False, False) in calls
    assert pixark.start_calls == 1
