import gamemodules.smallandserver as smallandserver
import gamemodules.stormworksserver as stormworksserver


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


def test_smallandserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("small")
    exe = tmp_path / "SMALLANDServer.sh"
    exe.write_text("")
    server.data.update({
        "dir": str(tmp_path) + "/",
        "exe_name": "SMALLANDServer.sh",
        "port": 7777,
        "worldname": "World",
        "servername": "AlphaGSM small",
        "serverpassword": "",
    })

    cmd, cwd = smallandserver.get_start_command(server)

    assert cmd[0] == "./SMALLANDServer.sh"
    assert cmd[-3:] == ["-port=7777", "-NOSTEAM", "-log"]
    assert cwd == server.data["dir"]


def test_stormworksserver_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    # Monkeypatch proton.wrap_command so the test is independent of Wine/Proton installation.
    monkeypatch.setattr(stormworksserver.proton, "wrap_command", lambda cmd, wineprefix=None: ["wine"] + list(cmd))

    server = DummyServer("storm")
    exe = tmp_path / "server64.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "server64.exe"})

    cmd, cwd = stormworksserver.get_start_command(server)

    assert "server64.exe" in cmd
    assert cwd == server.data["dir"]


def test_smalland_and_stormworks_updates_download_and_optionally_restart(monkeypatch):
    small = DummyServer("small")
    small.data["dir"] = "/srv/small/"
    storm = DummyServer("storm")
    storm.data["dir"] = "/srv/storm/"
    calls = []

    monkeypatch.setattr(
        smallandserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, force_windows=False: calls.append(
            (path, app_id, anon, validate)
        ),
    )

    smallandserver.update(small, validate=True, restart=True)
    stormworksserver.update(storm, validate=False, restart=False)

    assert ("/srv/small/", 808040, True, True) in calls
    assert ("/srv/storm/", 1247090, True, False) in calls
    assert small.start_calls == 1
