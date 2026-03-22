import gamemodules.gtafivemserver as gtafivemserver
import gamemodules.interstellarriftserver as interstellarriftserver
import gamemodules.mxbikesserver as mxbikesserver


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


def test_interstellarrift_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ir")
    exe = tmp_path / "InterstellarRiftServer.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "InterstellarRiftServer.x86_64",
            "port": 7777,
        }
    )

    cmd, cwd = interstellarriftserver.get_start_command(server)

    assert cmd[0] == "./InterstellarRiftServer.x86_64"
    assert "-port" in cmd
    assert cwd == server.data["dir"]


def test_mxbikes_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("mxb")
    exe = tmp_path / "mxbikes_dedicated"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "mxbikes_dedicated", "port": 54210})

    cmd, cwd = mxbikesserver.get_start_command(server)

    assert cmd == ["./mxbikes_dedicated", "54210"]
    assert cwd == server.data["dir"]


def test_fivem_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("fivem")
    exe = tmp_path / "run.sh"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "run.sh", "port": 30120})

    cmd, cwd = gtafivemserver.get_start_command(server)

    assert cmd[0] == "./run.sh"
    assert "sv_port" in cmd
    assert cwd == server.data["dir"]
