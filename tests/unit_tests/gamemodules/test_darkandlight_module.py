import gamemodules.darkandlightserver as darkandlightserver


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


def test_darkandlight_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    monkeypatch.setattr(
        darkandlightserver.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: wrap_calls.append(
            {"wineprefix": wineprefix, "prefer_proton": prefer_proton}
        ) or list(cmd),
    )
    server = DummyServer("dnl")
    exe_dir = tmp_path / "DNL" / "Binaries" / "Win64"
    exe_dir.mkdir(parents=True)
    exe = exe_dir / "DNLServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "DNL/Binaries/Win64/DNLServer.exe",
            "startmap": "DNL_ALL",
            "servername": "AlphaGSM dnl",
            "serverpassword": "",
            "adminpassword": "alphagsm",
            "port": 7777,
            "queryport": 27016,
            "maxplayers": 70,
        }
    )

    cmd, cwd = darkandlightserver.get_start_command(server)

    assert cmd[0] == "DNL/Binaries/Win64/DNLServer.exe"
    assert "DNL_ALL?listen?SessionName=AlphaGSM dnl" in cmd[1]
    assert "-nullRHI" in cmd
    assert "-log" in cmd
    assert "-unattended" in cmd
    assert cwd == str(tmp_path) + "/"
    assert wrap_calls == [{"wineprefix": None, "prefer_proton": True}]


def test_darkandlight_update_downloads_and_optionally_restart(monkeypatch):
    server = DummyServer("dnl")
    server.data["dir"] = "/srv/dnl/"
    calls = []

    monkeypatch.setattr(
        darkandlightserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    darkandlightserver.update(server, validate=True, restart=True)

    assert calls == [("/srv/dnl/", 630230, True, True)]
    assert server.start_calls == 1


def test_darkandlight_query_and_info_address_use_game_port_udp_on_linux(monkeypatch):
    server = DummyServer("dnl")
    server.data["port"] = "34121"
    server.data["queryport"] = "27016"
    monkeypatch.setattr(darkandlightserver, "IS_LINUX", True)
    monkeypatch.setattr(
        darkandlightserver.runtime_module,
        "resolve_query_host",
        lambda current: "10.0.0.10",
    )

    assert darkandlightserver.get_query_address(server) == ("10.0.0.10", 34121, "udp")
    assert darkandlightserver.get_info_address(server) == ("10.0.0.10", 34121, "udp")


def test_darkandlight_query_and_info_address_use_queryport_a2s_off_linux(monkeypatch):
    server = DummyServer("dnl")
    server.data["port"] = "34121"
    server.data["queryport"] = "27016"
    monkeypatch.setattr(darkandlightserver, "IS_LINUX", False)
    monkeypatch.setattr(
        darkandlightserver.runtime_module,
        "resolve_query_host",
        lambda current: "10.0.0.10",
    )

    assert darkandlightserver.get_query_address(server) == ("10.0.0.10", 27016, "a2s")
    assert darkandlightserver.get_info_address(server) == ("10.0.0.10", 27016, "a2s")
