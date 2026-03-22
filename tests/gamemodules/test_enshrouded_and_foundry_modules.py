import gamemodules.enshrouded as enshrouded
import gamemodules.foundryserver as foundryserver


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


def test_enshrouded_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ensh")
    exe = tmp_path / "enshrouded_server"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "enshrouded_server",
            "port": 15637,
            "queryport": 15638,
            "savegame": "ensh",
            "servername": "AlphaGSM ensh",
        }
    )

    cmd, cwd = enshrouded.get_start_command(server)

    assert cmd[0] == "./enshrouded_server"
    assert "--game-port" in cmd
    assert cwd == server.data["dir"]


def test_foundryserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("foundry")
    exe = tmp_path / "FoundryDedicatedServer"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "FoundryDedicatedServer",
            "worldname": "foundry",
            "servername": "AlphaGSM foundry",
            "port": 37200,
        }
    )

    cmd, cwd = foundryserver.get_start_command(server)

    assert cmd == ["./FoundryDedicatedServer", "--world", "foundry", "--name", "AlphaGSM foundry", "--port", "37200"]
    assert cwd == server.data["dir"]


def test_enshrouded_and_foundry_updates_download_and_optionally_restart(monkeypatch):
    ensh = DummyServer("ensh")
    ensh.data["dir"] = "/srv/ensh/"
    foundry = DummyServer("foundry")
    foundry.data["dir"] = "/srv/foundry/"
    calls = []

    monkeypatch.setattr(
        enshrouded.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True: calls.append((path, app_id, anon, validate)),
    )

    enshrouded.update(ensh, validate=True, restart=True)
    foundryserver.update(foundry, validate=False, restart=False)

    assert ("/srv/ensh/", 2278520, True, True) in calls
    assert ("/srv/foundry/", 2915550, True, False) in calls
    assert ensh.start_calls == 1
