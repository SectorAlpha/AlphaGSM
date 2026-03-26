import gamemodules.argoserver as argoserver
import gamemodules.bobserver as bobserver


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


def test_argoserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("argo")
    exe = tmp_path / "argo_server_x64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "argo_server_x64",
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "port": 2302,
            "bindaddress": "0.0.0.0",
            "mod": "",
        }
    )

    cmd, cwd = argoserver.get_start_command(server)

    assert cmd == [
        "./argo_server_x64",
        "-config",
        "server.cfg",
        "-profiles",
        "profiles",
        "-port",
        "2302",
        "-name",
        "argo",
        "-ip",
        "0.0.0.0",
    ]
    assert cwd == server.data["dir"]


def test_bobserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bob")
    exe = tmp_path / "BeastsOfBermudaServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "BeastsOfBermudaServer.sh",
            "port": 7777,
            "queryport": 7778,
            "servername": "AlphaGSM bob",
            "worldname": "bob",
            "password": "",
        }
    )

    cmd, cwd = bobserver.get_start_command(server)

    assert cmd == [
        "./BeastsOfBermudaServer.sh",
        "-log",
        "-port",
        "7777",
        "-queryport",
        "7778",
        "-servername",
        "AlphaGSM bob",
        "-world",
        "bob",
    ]
    assert cwd == server.data["dir"]


def test_argo_and_bob_updates_download_and_optionally_restart(monkeypatch):
    argo = DummyServer("argo")
    argo.data["dir"] = "/srv/argo/"
    bob = DummyServer("bob")
    bob.data["dir"] = "/srv/bob/"
    calls = []

    monkeypatch.setattr(
        argoserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    argoserver.update(argo, validate=True, restart=True)
    bobserver.update(bob, validate=False, restart=False)

    assert ("/srv/argo/", 563930, True, True) in calls
    assert ("/srv/bob/", 882430, True, False) in calls
    assert argo.start_calls == 1
