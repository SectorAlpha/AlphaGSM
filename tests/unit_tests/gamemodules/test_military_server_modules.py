import gamemodules.arma3server as arma3server
import gamemodules.armarserver as armarserver
import gamemodules.dayzserver as dayzserver
import gamemodules.squad44server as squad44server
import gamemodules.squadserver as squadserver


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


def test_arma3server_configure_sets_defaults(tmp_path):
    server = DummyServer("arma")

    arma3server.configure(server, ask=False, port=2302, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 233780
    assert server.data["configfile"] == "server.cfg"
    assert server.data["profilesdir"] == "profiles"


def test_arma3server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("arma")
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
        }
    )

    cmd, cwd = arma3server.get_start_command(server)

    assert cmd[0] == "./arma3server_x64"
    assert "-port=2302" in cmd
    assert cwd == server.data["dir"]


def test_armarserver_configure_sets_defaults(tmp_path):
    server = DummyServer("armar")

    armarserver.configure(server, ask=False, port=2001, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 1874900
    assert server.data["configfile"] == "configs/server.json"


def test_armarserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("armar")
    exe = tmp_path / "ArmaReforgerServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ArmaReforgerServer",
            "port": 2001,
            "configfile": "configs/server.json",
            "profilesdir": "profile",
            "bindaddress": "0.0.0.0",
        }
    )

    cmd, cwd = armarserver.get_start_command(server)

    assert cmd[0] == "./ArmaReforgerServer"
    assert "2001" in cmd
    assert cwd == server.data["dir"]


def test_dayzserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("dayz")
    exe = tmp_path / "DayZServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "DayZServer",
            "port": 2302,
            "configfile": "serverDZ.cfg",
            "profilesdir": "profiles",
            "cpu_count": "2",
        }
    )

    cmd, cwd = dayzserver.get_start_command(server)

    assert cmd[0] == "./DayZServer"
    assert "-config=serverDZ.cfg" in cmd
    assert cwd == server.data["dir"]


def test_squadserver_configure_sets_defaults(tmp_path):
    server = DummyServer("squad")

    squadserver.configure(server, ask=False, port=7787, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 403240
    assert server.data["queryport"] == "27165"


def test_squadserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("squad")
    exe = tmp_path / "SquadGameServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "SquadGameServer.sh",
            "port": 7787,
            "queryport": "27165",
            "fixedmaxplayers": "80",
        }
    )

    cmd, cwd = squadserver.get_start_command(server)

    assert cmd == ["./SquadGameServer.sh", "Port=7787", "QueryPort=27165", "FIXEDMAXPLAYERS=80"]
    assert cwd == server.data["dir"]


def test_squad44server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("s44")
    exe = tmp_path / "PostScriptumServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "PostScriptumServer.sh",
            "port": 7787,
            "queryport": "27165",
            "fixedmaxplayers": "80",
        }
    )

    cmd, cwd = squad44server.get_start_command(server)

    assert cmd == ["./PostScriptumServer.sh", "Port=7787", "QueryPort=27165", "FIXEDMAXPLAYERS=80"]
    assert cwd == server.data["dir"]


def test_military_modules_update_downloads_and_optional_restart(monkeypatch):
    arma_server = DummyServer("arma")
    arma_server.data["dir"] = "/srv/arma/"
    dayz_server = DummyServer("dayz")
    dayz_server.data["dir"] = "/srv/dayz/"
    squad_server = DummyServer("squad")
    squad_server.data["dir"] = "/srv/squad/"
    calls = []

    monkeypatch.setattr(
        arma3server.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    arma3server.update(arma_server, validate=True, restart=True)
    dayzserver.update(dayz_server, validate=False, restart=False)
    squadserver.update(squad_server, validate=False, restart=False)

    assert ("/srv/arma/", 233780, True, True) in calls
    assert ("/srv/dayz/", 223350, True, False) in calls
    assert ("/srv/squad/", 403240, True, False) in calls
    assert arma_server.start_calls == 1
