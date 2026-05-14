import gamemodules.atsserver as atsserver
import gamemodules.ets2server as ets2server


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


def test_atsserver_configure_sets_defaults(tmp_path):
    server = DummyServer("ats")

    atsserver.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 2239530
    assert server.data["configdir"] == ".local/share/American Truck Simulator"


def test_ets2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ets2")
    exe = tmp_path / "bin" / "linux_x64" / "eurotrucks2_server"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "bin/linux_x64/eurotrucks2_server",
            "port": 27015,
            "queryport": "27016",
        }
    )

    cmd, cwd = ets2server.get_start_command(server)

    assert cmd == ["./bin/linux_x64/eurotrucks2_server", "-ip", "0.0.0.0", "-port", "27015", "-query_port", "27016"]
    assert cwd == server.data["dir"]


def test_ets2server_query_and_info_use_dedicated_query_port(monkeypatch):
    observed = []

    def fake_resolve_query_host(server):
        observed.append(server.name)
        return "10.0.0.8"

    monkeypatch.setattr(ets2server.runtime_module, "resolve_query_host", fake_resolve_query_host)
    server = DummyServer("ets2")
    server.data["queryport"] = "27016"

    assert ets2server.get_query_address(server) == ("10.0.0.8", 27016, "a2s")
    assert ets2server.get_info_address(server) == ("10.0.0.8", 27016, "a2s")
    assert observed == ["ets2", "ets2"]


def test_trucksim_modules_update_downloads_and_optionally_restart(monkeypatch):
    ats = DummyServer("ats")
    ats.data["dir"] = "/srv/ats/"
    ets = DummyServer("ets")
    ets.data["dir"] = "/srv/ets/"
    calls = []

    monkeypatch.setattr(
        atsserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    atsserver.update(ats, validate=True, restart=True)
    ets2server.update(ets, validate=False, restart=False)

    assert ("/srv/ats/", 2239530, True, True) in calls
    assert ("/srv/ets/", 1948160, True, False) in calls
    assert ats.start_calls == 1
