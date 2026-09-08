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
    exe = tmp_path / "argoserver"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "argoserver",
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "port": 2302,
            "world": "empty",
            "mod": "",
        }
    )

    cmd, cwd = argoserver.get_start_command(server)

    assert cmd == [
        "./argoserver",
        "-config=server.cfg",
        "-port=2302",
        "-profiles=profiles",
        "-name=argo",
        "-world=empty",
    ]
    assert cwd == server.data["dir"]


def test_argoserver_queries_steam_port_above_game_port():
    server = DummyServer("argo")
    server.data["port"] = 2302

    assert argoserver.get_query_address(server) == ("127.0.0.1", 2303, "a2s")
    assert argoserver.get_info_address(server) == ("127.0.0.1", 2303, "a2s")
    server.data["port"] = 26000
    assert argoserver.get_info_address(server) == ("127.0.0.1", 26001, "a2s")


def test_argoserver_publishes_steam_query_and_master_ports(tmp_path):
    server = DummyServer("argo")
    server.data.update({"port": 26000, "dir": str(tmp_path), "exe_name": "argoserver",
                        "configfile": "server.cfg", "profilesdir": "profiles",
                        "world": "empty", "mod": ""})
    (tmp_path / "argoserver").touch()
    for spec in (argoserver.get_runtime_requirements(server), argoserver.get_container_spec(server)):
        ports = {(entry["host"], entry["container"], entry["protocol"]) for entry in spec["ports"]}
        assert {(26000, 26000, "udp"), (26001, 26001, "udp"), (26002, 26002, "udp")} <= ports


def test_bobserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("bob")
    exe = tmp_path / "LinuxServer/BeastsOfBermudaServer.sh"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "LinuxServer/BeastsOfBermudaServer.sh",
            "port": 7777,
            "queryport": 7778,
            "servername": "AlphaGSM bob",
            "worldname": "bob",
            "password": "",
        }
    )

    cmd, cwd = bobserver.get_start_command(server)

    assert cmd == [
        "./LinuxServer/BeastsOfBermudaServer.sh",
        "-log",
        "-NoVerifyGC",
        "-Port=7777",
        "-QueryPort=7778",
        "-SessionName",
        "AlphaGSM_bob",
        "-MapName",
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
        lambda path, app_id, anon, validate=True, **kwargs: calls.append(
            (path, app_id, anon, validate, kwargs)
        ),
    )

    argoserver.update(argo, validate=True, restart=True)
    bobserver.update(bob, validate=False, restart=False)

    assert ("/srv/argo/", 563930, True, True, {}) in calls
    assert ("/srv/bob/", 882430, True, False, {}) in calls
    assert argo.start_calls == 1
