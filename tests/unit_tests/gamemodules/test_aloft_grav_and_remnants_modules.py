import gamemodules.aloftserver as aloftserver
import gamemodules.gravserver as gravserver
import gamemodules.remnantsserver as remnantsserver


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


def test_aloft_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("aloft")
    exe = tmp_path / "AloftServerNoGuiLoad.ps1"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "AloftServerNoGuiLoad.ps1",
            "mapname": "AloftWorld",
            "servername": "SkyServer",
            "visible": "true",
            "privateislands": "false",
            "playercount": 8,
            "port": 0,
        }
    )

    cmd, cwd = aloftserver.get_start_command(server)

    assert cmd[0:2] == ["pwsh", "./AloftServerNoGuiLoad.ps1"]
    assert "load#AloftWorld#" in cmd
    assert "servername#SkyServer#" in cmd
    assert cwd == server.data["dir"]


def test_grav_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("grav")
    exe = tmp_path / "CAGGameServer-Win32-Shipping"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "CAGGameServer-Win32-Shipping",
            "port": 7777,
            "peerport": 7778,
            "queryport": 27015,
            "maxplayers": 32,
            "servername": "GravServer",
            "adminpassword": "",
        }
    )

    cmd, cwd = gravserver.get_start_command(server)

    assert cmd[0] == "./CAGGameServer-Win32-Shipping"
    assert "Port=7777" in cmd[1]
    assert 'ServerName="GravServer"' in cmd[1]
    assert cwd == server.data["dir"]


def test_remnants_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(
        remnantsserver.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: list(cmd),
    )
    server = DummyServer("remnants")
    exe = tmp_path / "RemSurvivalServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "RemSurvivalServer.exe",
            "port": 7777,
            "queryport": 27015,
        }
    )

    cmd, cwd = remnantsserver.get_start_command(server)

    assert cmd == ["RemSurvivalServer.exe", "-MultiHome=0.0.0.0", "-Port=7777", "-QueryPort=27015", "-log", "-unattended"]
    assert cwd == server.data["dir"]


def test_remnants_update_downloads_and_optionally_restart(monkeypatch):
    server = DummyServer("remnants")
    server.data["dir"] = "/srv/remnants/"
    calls = []

    monkeypatch.setattr(
        remnantsserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    remnantsserver.update(server, validate=True, restart=True)

    assert calls == [("/srv/remnants/", 1141420, True, True)]
    assert server.start_calls == 1
