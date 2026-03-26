import gamemodules.ark as ark
import gamemodules.unturned as unturned


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


def test_ark_configure_sets_defaults(tmp_path):
    server = DummyServer("arkalpha")

    args, kwargs = ark.configure(server, ask=False, port=7777, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["Steam_AppID"] == 376030
    assert server.data["map"] == "TheIsland"
    assert server.data["queryport"] == "27015"


def test_ark_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("arkalpha")
    exe = tmp_path / "ShooterGame" / "Binaries" / "Linux" / "ShooterGameServer"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ShooterGame/Binaries/Linux/ShooterGameServer",
            "map": "TheIsland",
            "sessionname": "AlphaGSM arkalpha",
            "port": 7777,
            "queryport": "27015",
            "maxplayers": "70",
            "adminpassword": "alphagsm",
            "serverpassword": "",
        }
    )

    cmd, cwd = ark.get_start_command(server)

    assert cmd[0] == "./ShooterGame/Binaries/Linux/ShooterGameServer"
    assert "TheIsland?listen?SessionName=AlphaGSM arkalpha?Port=7777?QueryPort=27015?MaxPlayers=70?ServerAdminPassword=alphagsm" in cmd[1]
    assert cwd == server.data["dir"]


def test_unturned_configure_sets_defaults(tmp_path):
    server = DummyServer("untalpha")

    unturned.configure(server, ask=False, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 1110390
    assert server.data["serverid"] == "untalpha"
    assert server.data["launchmode"] == "InternetServer"


def test_unturned_get_start_command_uses_serverhelper(tmp_path):
    server = DummyServer("untalpha")
    exe = tmp_path / "ServerHelper.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "ServerHelper.sh", "launchmode": "InternetServer", "serverid": "untalpha"})

    cmd, cwd = unturned.get_start_command(server)

    assert cmd == ["./ServerHelper.sh", "+InternetServer/untalpha"]
    assert cwd == server.data["dir"]


def test_ark_and_unturned_update_and_restart(monkeypatch):
    ark_server = DummyServer("ark")
    ark_server.data["dir"] = "/srv/ark/"
    unt_server = DummyServer("unt")
    unt_server.data["dir"] = "/srv/unturned/"
    calls = []

    monkeypatch.setattr(
        ark.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    ark.update(ark_server, validate=True, restart=True)
    unturned.update(unt_server, validate=False, restart=False)

    assert ("/srv/ark/", 376030, True, True) in calls
    assert ("/srv/unturned/", 1110390, True, False) in calls
    assert ark_server.start_calls == 1
    assert unt_server.start_calls == 0
