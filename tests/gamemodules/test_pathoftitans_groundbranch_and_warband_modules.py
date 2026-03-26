import gamemodules.groundbranchserver as groundbranchserver
import gamemodules.pathoftitansserver as pathoftitansserver
import gamemodules.warbandserver as warbandserver


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


def test_pathoftitans_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("pot")
    exe = tmp_path / "PathOfTitansServer.sh"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "PathOfTitansServer.sh",
            "port": 7777,
            "server_name": "AlphaGSM_pot",
            "maxplayers": "100",
            "server_guid": "test-guid-1234",
        }
    )

    cmd, cwd = pathoftitansserver.get_start_command(server)

    assert cmd[0] == "./PathOfTitansServer.sh"
    assert "-port=7777" in cmd
    assert cwd == server.data["dir"]


def test_groundbranch_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("gb")
    exe = tmp_path / "GroundBranchServer-Win64-Shipping.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "GroundBranchServer-Win64-Shipping.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 16,
        }
    )

    cmd, cwd = groundbranchserver.get_start_command(server)

    assert cmd[0] == "./GroundBranchServer-Win64-Shipping.exe"
    assert "-QueryPort=27015" in cmd
    assert cwd == server.data["dir"]


def test_warband_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("warband")
    exe = tmp_path / "mb_warband_dedicated"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "mb_warband_dedicated",
            "port": 7240,
            "maxplayers": 64,
        }
    )

    cmd, cwd = warbandserver.get_start_command(server)

    assert cmd[0] == "./mb_warband_dedicated"
    assert "-p" in cmd
    assert cwd == server.data["dir"]


def test_groundbranch_update_downloads_and_optionally_restart(monkeypatch):
    server = DummyServer("gb")
    server.data["dir"] = "/srv/groundbranch/"
    calls = []

    monkeypatch.setattr(
        groundbranchserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    groundbranchserver.update(server, validate=True, restart=True)

    assert ("/srv/groundbranch/", 476400, True, True) in calls
    assert server.start_calls == 1
