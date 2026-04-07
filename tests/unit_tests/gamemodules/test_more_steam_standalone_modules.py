import gamemodules.projectzomboid as projectzomboid
import gamemodules.satisfactory as satisfactory


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


def test_projectzomboid_configure_sets_defaults(tmp_path):
    server = DummyServer("pzalpha")

    args, kwargs = projectzomboid.configure(server, ask=False, port=16261, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["Steam_AppID"] == 380870
    assert server.data["servername"] == "pzalpha"
    assert server.data["adminpassword"] == "alphagsm"
    assert server.data["queryport"] == 16262
    assert server.data["backupfiles"] == ["Zomboid", "Server", "start-server.sh"]


def test_projectzomboid_get_start_command_uses_server_name(tmp_path):
    server = DummyServer("pzalpha")
    exe = tmp_path / "start-server.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "start-server.sh", "servername": "pzalpha", "adminpassword": "alphagsm", "port": "16261"})

    cmd, cwd = projectzomboid.get_start_command(server)

    assert cmd == ["./start-server.sh", "-servername", "pzalpha", "-adminpassword", "alphagsm", "-port", "16261"]
    assert cwd == server.data["dir"]


def test_satisfactory_configure_sets_defaults(tmp_path):
    server = DummyServer("sfalpha")

    satisfactory.configure(server, ask=False, port=7777, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 1690800
    assert server.data["queryport"] == "7778"
    assert server.data["backupfiles"] == ["FactoryGame/Saved", "FactoryServer.sh"]


def test_satisfactory_get_start_command_uses_ports(tmp_path):
    server = DummyServer("sfalpha")
    exe = tmp_path / "FactoryServer.sh"
    exe.write_text("")
    server.data.update(
        {"dir": str(tmp_path) + "/", "exe_name": "FactoryServer.sh", "port": 7777, "queryport": "15777"}
    )

    cmd, cwd = satisfactory.get_start_command(server)

    assert "./FactoryServer.sh" == cmd[0]
    assert "-Port=7777" in cmd
    assert "-QueryPort=15777" in cmd
    assert cwd == server.data["dir"]


def test_more_standalone_steam_modules_update_and_restart(monkeypatch):
    pz_server = DummyServer("pz")
    pz_server.data["dir"] = "/srv/pz/"
    sf_server = DummyServer("sf")
    sf_server.data["dir"] = "/srv/sf/"
    calls = []

    monkeypatch.setattr(
        projectzomboid.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    projectzomboid.update(pz_server, validate=True, restart=True)
    satisfactory.update(sf_server, validate=False, restart=False)

    assert ("/srv/pz/", 380870, True, True) in calls
    assert ("/srv/sf/", 1690800, True, False) in calls
    assert pz_server.start_calls == 1
    assert sf_server.start_calls == 0
