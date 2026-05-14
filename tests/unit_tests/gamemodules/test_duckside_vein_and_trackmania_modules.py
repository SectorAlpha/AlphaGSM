import gamemodules.ducksideserver as ducksideserver
import gamemodules.trackmaniaserver as trackmaniaserver
import gamemodules.veinserver as veinserver


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


def test_duckside_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    wrap_calls = []

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        wrap_calls.append(prefer_proton)
        return list(cmd)

    monkeypatch.setattr(ducksideserver.proton, "wrap_command", fake_wrap_command)
    server = DummyServer("duck")
    exe = tmp_path / "DucksideServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "DucksideServer.exe",
            "port": 7777,
            "queryport": 27015,
        }
    )

    cmd, cwd = ducksideserver.get_start_command(server)

    assert cmd == ["DucksideServer.exe", "-log", "-port", "7777", "-queryport", "27015"]
    assert cwd == server.data["dir"]
    assert wrap_calls == [True]


def test_vein_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("vein")
    exe = tmp_path / "VeinServer.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "VeinServer.sh", "port": 7777})

    cmd, cwd = veinserver.get_start_command(server)

    assert cmd == ["./VeinServer.sh", "-Port=7777"]
    assert cwd == server.data["dir"]


def test_trackmania_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("trackmania")
    exe = tmp_path / "TrackmaniaServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "TrackmaniaServer",
            "dedicated_cfg": "dedicated_cfg.txt",
            "game_settings": "MatchSettings/Nations/NationsGreen.txt",
        }
    )

    cmd, cwd = trackmaniaserver.get_start_command(server)

    assert cmd == [
        "./TrackmaniaServer",
        "/dedicated_cfg=dedicated_cfg.txt",
        "/game_settings=MatchSettings/Nations/NationsGreen.txt",
    ]
    assert cwd == server.data["dir"]


def test_duckside_and_vein_updates_download_and_optionally_restart(monkeypatch):
    duck = DummyServer("duck")
    duck.data["dir"] = "/srv/duck/"
    vein = DummyServer("vein")
    vein.data["dir"] = "/srv/vein/"
    calls = []

    monkeypatch.setattr(
        ducksideserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append((path, app_id, anon, validate)),
    )

    ducksideserver.update(duck, validate=True, restart=True)
    veinserver.update(vein, validate=False, restart=False)

    assert ("/srv/duck/", 2690320, False, True) in calls
    assert ("/srv/vein/", 2131400, True, False) in calls
    assert duck.start_calls == 1


def test_trackmania_configure_stores_url_and_defaults(tmp_path):
    server = DummyServer("trackmania")

    trackmaniaserver.configure(
        server,
        ask=False,
        port=5000,
        dir=str(tmp_path),
        url="https://example.com/trackmania.zip",
        download_name="trackmania.zip",
    )

    assert server.data["port"] == 5000
    assert server.data["url"] == "https://example.com/trackmania.zip"
    assert server.data["download_name"] == "trackmania.zip"
    assert server.data["exe_name"] == "TrackmaniaServer"
