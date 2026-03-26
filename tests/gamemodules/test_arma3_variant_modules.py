import gamemodules.arma3epochserver as arma3epochserver
import gamemodules.arma3exileserver as arma3exileserver
import gamemodules.arma3headlessserver as arma3headlessserver
import gamemodules.arma3wastelandserver as arma3wastelandserver


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


def test_arma3epochserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("epoch")
    exe = tmp_path / "arma3server_x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma3server_x64",
            "port": 2302,
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "empty",
            "mod": "@Epoch;@EpochHive",
            "servermod": "@epochhive",
        }
    )

    cmd, cwd = arma3epochserver.get_start_command(server)

    assert "-mod=@Epoch;@EpochHive" in cmd
    assert "-serverMod=@epochhive" in cmd
    assert cwd == server.data["dir"]


def test_arma3exileserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("exile")
    exe = tmp_path / "arma3server_x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma3server_x64",
            "port": 2302,
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "empty",
            "mod": "@Exile",
            "servermod": "@ExileServer",
        }
    )

    cmd, cwd = arma3exileserver.get_start_command(server)

    assert "-mod=@Exile" in cmd
    assert "-serverMod=@ExileServer" in cmd
    assert cwd == server.data["dir"]


def test_arma3headlessserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("headless")
    exe = tmp_path / "arma3server_x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma3server_x64",
            "port": 2302,
            "profilesdir": "profiles",
            "connect": "127.0.0.1",
            "password": "",
            "mod": "",
        }
    )

    cmd, cwd = arma3headlessserver.get_start_command(server)

    assert "-client" in cmd
    assert "-connect=127.0.0.1" in cmd
    assert cwd == server.data["dir"]


def test_arma3wastelandserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("waste")
    exe = tmp_path / "arma3server_x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "arma3server_x64",
            "port": 2302,
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "Altis",
            "mod": "",
            "mission": "A3Wasteland_v1.3.Stratis",
        }
    )

    cmd, cwd = arma3wastelandserver.get_start_command(server)

    assert "-mission=A3Wasteland_v1.3.Stratis" in cmd
    assert "-world=Altis" in cmd
    assert cwd == server.data["dir"]


def test_arma3_variant_modules_update_downloads_and_optional_restart(monkeypatch):
    epoch = DummyServer("epoch")
    epoch.data["dir"] = "/srv/epoch/"
    exile = DummyServer("exile")
    exile.data["dir"] = "/srv/exile/"
    headless = DummyServer("headless")
    headless.data["dir"] = "/srv/headless/"
    calls = []

    monkeypatch.setattr(
        arma3epochserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    arma3epochserver.update(epoch, validate=True, restart=True)
    arma3exileserver.update(exile, validate=False, restart=False)
    arma3headlessserver.update(headless, validate=False, restart=False)

    assert ("/srv/epoch/", 233780, True, True) in calls
    assert ("/srv/exile/", 233780, True, False) in calls
    assert ("/srv/headless/", 233780, True, False) in calls
    assert epoch.start_calls == 1
