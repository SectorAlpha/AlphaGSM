import gamemodules.acserver as acserver
import gamemodules.mordserver as mordserver
import gamemodules.pvrserver as pvrserver


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


def test_acserver_configure_sets_defaults(tmp_path):
    server = DummyServer("ac")

    acserver.configure(server, ask=False, port=9600, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 302550
    assert server.data["configfile"] == "cfg/server_cfg.ini"


def test_mordserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("mord")
    exe = tmp_path / "MordhauServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "MordhauServer.sh", "map": "ThePit", "port": 7777, "queryport": "27015"})

    cmd, cwd = mordserver.get_start_command(server)

    assert cmd == ["./MordhauServer.sh", "ThePit", "-port=7777", "-queryport=27015"]
    assert cwd == server.data["dir"]


def test_mordserver_query_addresses_use_udp_game_port():
    server = DummyServer("mord")
    server.data.update({"port": 7777, "queryport": "27015"})

    assert mordserver.get_query_address(server) == ("127.0.0.1", 7777, "udp")
    assert mordserver.get_info_address(server) == ("127.0.0.1", 7777, "udp")


def test_pvrserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("pvr")
    exe = tmp_path / "PavlovServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "PavlovServer.sh", "map": "UGC1664/SND", "port": 7777, "queryport": "9100"})

    cmd, cwd = pvrserver.get_start_command(server)

    assert cmd == ["./PavlovServer.sh", "-PORT=7777", "-QueryPort=9100", "-Map=UGC1664/SND"]
    assert cwd == server.data["dir"]


def test_tactical_modules_update_downloads_and_optionally_restart(monkeypatch):
    ac = DummyServer("ac")
    ac.data["dir"] = "/srv/ac/"
    mord = DummyServer("mord")
    mord.data["dir"] = "/srv/mord/"
    pvr = DummyServer("pvr")
    pvr.data["dir"] = "/srv/pvr/"
    calls = []

    monkeypatch.setattr(
        acserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    acserver.update(ac, validate=True, restart=True)
    mordserver.update(mord, validate=False, restart=False)
    pvrserver.update(pvr, validate=False, restart=False)

    assert ("/srv/ac/", 302550, True, True) in calls
    assert ("/srv/mord/", 629800, True, False) in calls
    assert ("/srv/pvr/", 622970, True, False) in calls
    assert ac.start_calls == 1
