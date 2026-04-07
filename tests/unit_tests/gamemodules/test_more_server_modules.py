import gamemodules.inssserver as inssserver
import gamemodules.necserver as necserver
import gamemodules.scpslserver as scpslserver


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


def test_inssserver_configure_sets_defaults(tmp_path):
    server = DummyServer("sandstorm")

    inssserver.configure(server, ask=False, port=27102, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 581330
    assert server.data["queryport"] == "27103"  # port+1
    assert server.data["maxplayers"] == "28"


def test_inssserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("sandstorm")
    exe = tmp_path / "InsurgencyServer-Linux-Shipping"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "InsurgencyServer-Linux-Shipping",
            "port": 27102,
            "queryport": "27131",
            "hostname": "AlphaGSM sandstorm",
            "mapcycle": "Scenario_Crossing_Push_Security",
            "maxplayers": "28",
            "gslt": "",
        }
    )

    cmd, cwd = inssserver.get_start_command(server)

    assert cmd[0] == "./InsurgencyServer-Linux-Shipping"
    assert "-Port=27102" in cmd
    assert cwd == server.data["dir"]


def test_necserver_configure_sets_defaults(tmp_path):
    server = DummyServer("nec")

    necserver.configure(server, ask=False, port=14159, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 1169370
    assert server.data["slots"] == "10"
    assert server.data["world"] == "nec"


def test_necserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("nec")
    exe = tmp_path / "Server.jar"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Server.jar",
            "javapath": "java",
            "world": "nec",
            "port": 14159,
            "slots": "10",
        }
    )

    cmd, cwd = necserver.get_start_command(server)

    assert cmd == ["java", "-jar", "Server.jar", "-nogui", "-world", "nec", "-port", "14159", "-slots", "10"]
    assert cwd == server.data["dir"]


def test_scpslserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("scpsl")
    exe = tmp_path / "LocalAdmin"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "LocalAdmin",
            "port": 7777,
            "queryport": "7778",
        }
    )

    cmd, cwd = scpslserver.get_start_command(server)

    assert cmd == [
        "env",
        f"HOME={tmp_path / 'home'}",
        f"XDG_CONFIG_HOME={tmp_path / 'home' / '.config'}",
        "./LocalAdmin",
        "7777",
    ]
    assert cwd == server.data["dir"]


def test_new_modules_update_downloads_and_optional_restart(monkeypatch):
    inss_server = DummyServer("sandstorm")
    inss_server.data["dir"] = "/srv/inss/"
    nec_server = DummyServer("nec")
    nec_server.data["dir"] = "/srv/nec/"
    scp_server = DummyServer("scp")
    scp_server.data["dir"] = "/srv/scp/"
    calls = []

    monkeypatch.setattr(
        inssserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    inssserver.update(inss_server, validate=True, restart=True)
    necserver.update(nec_server, validate=False, restart=False)
    scpslserver.update(scp_server, validate=False, restart=False)

    assert ("/srv/inss/", 581330, True, True) in calls
    assert ("/srv/nec/", 1169370, True, False) in calls
    assert ("/srv/scp/", 996560, True, False) in calls
    assert inss_server.start_calls == 1
