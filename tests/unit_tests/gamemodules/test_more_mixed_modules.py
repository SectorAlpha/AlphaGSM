import gamemodules.accserver as accserver
import gamemodules.alienarenaserver as alienarenaserver
import gamemodules.etlegacyserver as etlegacyserver


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


def test_accserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("acc")
    exe_dir = tmp_path / "server"
    exe_dir.mkdir()
    exe = exe_dir / "accServer.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "server/accServer.exe", "configdir": "cfg"})

    cmd, cwd = accserver.get_start_command(server)

    assert cmd == ["./server/accServer.exe", str(tmp_path / "cfg")]
    assert cwd == server.data["dir"]


def test_etlegacyserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("etl")
    exe = tmp_path / "etl.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "etl.x86_64",
            "fs_game": "legacy",
            "hostname": "AlphaGSM etl",
            "configfile": "etl_server.cfg",
            "port": 27960,
        }
    )

    cmd, cwd = etlegacyserver.get_start_command(server)

    assert cmd[0] == "./etl.x86_64"
    assert "sv_hostname" in cmd
    assert cwd == server.data["dir"]


def test_alienarenaserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("aa")
    exe = tmp_path / "crx-dedicated"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "crx-dedicated",
            "game": "arena",
            "hostname": "AlphaGSM aa",
            "startmap": "dm-deathvalley",
            "port": 27910,
        }
    )

    cmd, cwd = alienarenaserver.get_start_command(server)

    assert cmd[0] == "./crx-dedicated"
    assert "hostname" in cmd
    assert cwd == server.data["dir"]


def test_mixed_modules_update_downloads_and_optionally_restart(monkeypatch):
    acc = DummyServer("acc")
    acc.data["dir"] = "/srv/acc/"
    calls = []

    monkeypatch.setattr(
        accserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    accserver.update(acc, validate=True, restart=True)

    assert ("/srv/acc/", 1430110, True, True) in calls
    assert acc.start_calls == 1
