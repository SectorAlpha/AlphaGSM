import gamemodules.starbound as starbound
import gamemodules.valheim as valheim


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


def test_valheim_configure_sets_defaults(tmp_path):
    server = DummyServer("valheim")

    args, kwargs = valheim.configure(server, ask=False, port=2456, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["Steam_AppID"] == 896660
    assert server.data["worldname"] == "valheim"
    assert server.data["serverpassword"] == "alphagsm"
    assert server.data["backupfiles"] == ["worlds", "start_server.sh"]


def test_valheim_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("valheim")
    exe = tmp_path / "valheim_server.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "valheim_server.x86_64",
            "servername": "AlphaGSM valheim",
            "port": 2456,
            "worldname": "myworld",
            "serverpassword": "alphagsm",
            "public": "0",
        }
    )

    cmd, cwd = valheim.get_start_command(server)

    assert cmd[0] == "./valheim_server.x86_64"
    assert "-world" in cmd
    assert "myworld" in cmd
    assert "-savedir" in cmd
    assert cwd == server.data["dir"]


def test_starbound_configure_sets_defaults(tmp_path):
    server = DummyServer("star")

    starbound.configure(server, ask=False, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 211820
    assert server.data["backupfiles"] == ["giraffe_storage", "linux64/sbboot.config"]
    assert server.data["exe_name"] == "linux64/starbound_server"


def test_starbound_get_start_command_uses_linux64_binary(tmp_path):
    server = DummyServer("star")
    exe = tmp_path / "linux64" / "starbound_server"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "linux64/starbound_server"})

    cmd, cwd = starbound.get_start_command(server)

    assert cmd == ["./linux64/starbound_server"]
    assert cwd == server.data["dir"]


def test_standalone_steam_module_updates_download_and_restart(monkeypatch):
    valheim_server = DummyServer("valheim")
    valheim_server.data["dir"] = "/srv/valheim/"
    starbound_server = DummyServer("star")
    starbound_server.data["dir"] = "/srv/starbound/"
    calls = []

    monkeypatch.setattr(
        valheim.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    valheim.update(valheim_server, validate=True, restart=True)
    starbound.update(starbound_server, validate=False, restart=False)

    assert ("/srv/valheim/", 896660, True, True) in calls
    assert ("/srv/starbound/", 211820, True, False) in calls
    assert valheim_server.start_calls == 1
    assert starbound_server.start_calls == 0
