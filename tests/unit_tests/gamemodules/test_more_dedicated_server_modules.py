import gamemodules.askaserver as askaserver
import gamemodules.astroneerserver as astroneerserver
import gamemodules.atlasserver as atlasserver


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


def test_askaserver_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        wrap_calls.append(prefer_proton)
        return list(cmd)

    monkeypatch.setattr(askaserver.proton, "wrap_command", fake_wrap_command)
    server = DummyServer("aska")
    exe = tmp_path / "AskaServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "AskaServer.exe",
            "port": 27015,
            "queryport": 27016,
            "servername": "aska",
            "displayname": "AlphaGSM aska",
            "maxplayers": 4,
            "password": "",
        }
    )

    cmd, cwd = askaserver.get_start_command(server)

    assert cmd == [
        "AskaServer.exe",
        "-batchmode",
        "-nographics",
        "-logFile",
        "./server.log",
        "-Port",
        "27015",
        "-QueryPort",
        "27016",
        "-ServerName",
        "aska",
        "-DisplayName",
        "AlphaGSM aska",
        "-MaxPlayers",
        "4",
    ]
    assert cwd == server.data["dir"]
    assert wrap_calls == [True]


def test_askaserver_runtime_requirements_use_wine_proton_family(tmp_path, monkeypatch):
    monkeypatch.setattr(askaserver, "IS_LINUX", True)
    monkeypatch.setattr(
        askaserver.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "/usr/bin/wine",
        ]
        + list(cmd),
    )
    server = DummyServer("aska")
    (tmp_path / "AskaServer.exe").write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "AskaServer.exe",
            "port": 27015,
            "queryport": 27016,
            "servername": "aska",
            "displayname": "AlphaGSM aska",
            "maxplayers": 4,
            "password": "",
        }
    )

    requirements = askaserver.get_runtime_requirements(server)
    spec = askaserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "wine-proton"
    assert requirements["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27016, "container": 27016, "protocol": "udp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "AskaServer.exe"


def test_astroneerserver_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        wrap_calls.append(prefer_proton)
        return list(cmd)

    monkeypatch.setattr(astroneerserver.proton, "wrap_command", fake_wrap_command)
    server = DummyServer("astro")
    exe = tmp_path / "AstroServer.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "AstroServer.exe"})

    cmd, cwd = astroneerserver.get_start_command(server)

    assert cmd == ["AstroServer.exe"]
    assert cwd == server.data["dir"]
    assert wrap_calls == [True]


def test_atlasserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("atlas")
    exe_dir = tmp_path / "ShooterGame" / "Binaries" / "Linux"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "ShooterGameServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ShooterGame/Binaries/Linux/ShooterGameServer",
            "map": "Ocean",
            "sessionname": "AlphaGSM atlas",
            "port": 57555,
            "queryport": 57561,
            "maxplayers": 100,
            "adminpassword": "alphagsm",
            "serverpassword": "",
        }
    )

    cmd, cwd = atlasserver.get_start_command(server)

    assert cmd == [
        "./ShooterGame/Binaries/Linux/ShooterGameServer",
        "Ocean?listen?SessionName=AlphaGSM atlas?Port=57555?QueryPort=57561?MaxPlayers=100?ServerAdminPassword=alphagsm",
        "-server",
        "-log",
    ]
    assert cwd == server.data["dir"]


def test_more_dedicated_modules_update_downloads_and_optionally_restart(monkeypatch):
    aska = DummyServer("aska")
    aska.data["dir"] = "/srv/aska/"
    astro = DummyServer("astro")
    astro.data["dir"] = "/srv/astro/"
    atlas = DummyServer("atlas")
    atlas.data["dir"] = "/srv/atlas/"
    calls = []

    monkeypatch.setattr(
        askaserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    askaserver.update(aska, validate=True, restart=True)
    astroneerserver.update(astro, validate=False, restart=False)
    atlasserver.update(atlas, validate=False, restart=False)

    assert ("/srv/aska/", 3246670, True, True) in calls
    assert ("/srv/astro/", 728470, True, False) in calls
    assert ("/srv/atlas/", 1006030, True, False) in calls
    assert aska.start_calls == 1
