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
    exe = tmp_path / "start-server.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "start-server.sh"})

    cmd, cwd = smallandserver.get_start_command(server)

    assert cmd == ["./start-server.sh"]
    assert cwd == server.data["dir"]


def test_stormworksserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("storm")
    exe = tmp_path / "server64.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "server64.exe"})

    cmd, cwd = stormworksserver.get_start_command(server)

    assert cmd == ["./server64.exe"]
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
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    smallandserver.update(small, validate=True, restart=True)
    stormworksserver.update(storm, validate=False, restart=False)

    assert ("/srv/small/", 808040, True, True) in calls
    assert ("/srv/storm/", 1247090, True, False) in calls
    assert small.start_calls == 1
