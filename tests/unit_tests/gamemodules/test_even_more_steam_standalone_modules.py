import gamemodules.rust as rust
import gamemodules.sevendaystodie as sdtd


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


def test_rust_configure_sets_defaults(tmp_path):
    server = DummyServer("rustalpha")

    args, kwargs = rust.configure(server, ask=False, port=28015, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["Steam_AppID"] == 258550
    assert server.data["hostname"] == "AlphaGSM rustalpha"
    assert server.data["rconport"] == "28016"


def test_rust_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("rustalpha")
    exe = tmp_path / "RustDedicated"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "RustDedicated",
            "port": 28015,
            "hostname": "AlphaGSM rustalpha",
            "level": "Procedural Map",
            "worldsize": "3000",
            "maxplayers": "50",
            "seed": "12345",
            "rconport": "28016",
        }
    )

    cmd, cwd = rust.get_start_command(server)

    assert cmd[0] == "./RustDedicated"
    assert "+server.port" in cmd
    assert "28015" in cmd
    assert "+rcon.port" in cmd
    assert cwd == server.data["dir"]


def test_sdtd_configure_sets_defaults(tmp_path):
    server = DummyServer("sdtdalpha")

    sdtd.configure(server, ask=False, port=26900, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 294420
    assert server.data["configfile"] == "serverconfig.xml"
    assert server.data["backupfiles"] == ["Saves", "Mods", "serverconfig.xml", "startserver.sh"]


def test_sdtd_get_start_command_uses_configfile(tmp_path):
    server = DummyServer("sdtdalpha")
    exe = tmp_path / "startserver.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "startserver.sh", "configfile": "serverconfig.xml"})

    cmd, cwd = sdtd.get_start_command(server)

    assert cmd == ["./startserver.sh", "-configfile=serverconfig.xml"]
    assert cwd == server.data["dir"]


def test_rust_and_sdtd_update_and_restart(monkeypatch):
    rust_server = DummyServer("rust")
    rust_server.data["dir"] = "/srv/rust/"
    sdtd_server = DummyServer("sdtd")
    sdtd_server.data["dir"] = "/srv/sdtd/"
    calls = []

    monkeypatch.setattr(
        rust.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    rust.update(rust_server, validate=True, restart=True)
    sdtd.update(sdtd_server, validate=False, restart=False)

    assert ("/srv/rust/", 258550, True, True) in calls
    assert ("/srv/sdtd/", 294420, True, False) in calls
    assert rust_server.start_calls == 1
    assert sdtd_server.start_calls == 0
