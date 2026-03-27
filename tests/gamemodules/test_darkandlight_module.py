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
    monkeypatch.setattr(darkandlightserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
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
    assert cwd == server.data["dir"]


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
