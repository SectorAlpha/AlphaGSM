import gamemodules.pcarserver as pcarserver
import gamemodules.pcars2server as pcars2server
import gamemodules.stationeersserver as stationeersserver


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


def test_pcarserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("pc1")
    exe = tmp_path / "DedicatedServerCmd"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "DedicatedServerCmd", "configfile": "server.cfg"})

    cmd, cwd = pcarserver.get_start_command(server)

    assert cmd == ["./DedicatedServerCmd"]
    assert cwd == server.data["dir"]


def test_pcars2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("pc2")
    exe = tmp_path / "DedicatedServerCmd"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "DedicatedServerCmd", "configfile": "server.cfg"})

    cmd, cwd = pcars2server.get_start_command(server)

    assert cmd == ["./DedicatedServerCmd"]
    assert cwd == server.data["dir"]


def test_stationeersserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("st")
    exe = tmp_path / "rocketstation_DedicatedServer.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "rocketstation_DedicatedServer.x86_64",
            "savename": "st",
            "worldname": "Space",
            "servername": "AlphaGSM st",
            "port": 27500,
            "updateport": 27015,
            "autosave": "true",
            "saveinterval": 300,
            "serverpassword": "",
            "maxplayers": 10,
            "upnp": "false",
        }
    )

    cmd, cwd = stationeersserver.get_start_command(server)

    assert cmd[0] == "./rocketstation_DedicatedServer.x86_64"
    assert "GamePort" in cmd
    assert "UpdatePort" in cmd
    assert cwd == server.data["dir"]


def test_more_simulation_modules_update_downloads_and_optionally_restart(monkeypatch):
    pc1 = DummyServer("pc1")
    pc1.data["dir"] = "/srv/pc1/"
    pc2 = DummyServer("pc2")
    pc2.data["dir"] = "/srv/pc2/"
    st = DummyServer("st")
    st.data["dir"] = "/srv/st/"
    calls = []

    monkeypatch.setattr(
        pcarserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    pcarserver.update(pc1, validate=True, restart=True)
    pcars2server.update(pc2, validate=False, restart=False)
    stationeersserver.update(st, validate=False, restart=False)

    assert ("/srv/pc1/", 332670, True, True) in calls
    assert ("/srv/pc2/", 413770, True, False) in calls
    assert ("/srv/st/", 600760, True, False) in calls
    assert pc1.start_calls == 1
