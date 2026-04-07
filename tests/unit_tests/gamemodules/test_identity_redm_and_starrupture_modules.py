import gamemodules.redmserver as redmserver
import gamemodules.starruptureserver as starruptureserver


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


def test_redm_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("redm")
    exe = tmp_path / "run.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "run.sh", "port": 30120})

    cmd, cwd = redmserver.get_start_command(server)

    assert cmd[0] == "./run.sh"
    assert "sv_port" in cmd
    assert cwd == server.data["dir"]


def test_starrupture_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    monkeypatch.setattr(starruptureserver.proton, "wrap_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer("star")
    exe = tmp_path / "StarRuptureServer.x86_64"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "StarRuptureServer.x86_64", "port": 7777})

    cmd, cwd = starruptureserver.get_start_command(server)

    assert cmd == ["StarRuptureServer.x86_64", "--port", "7777"]
    assert cwd == server.data["dir"]
