import gamemodules.mtaserver as mtaserver
import gamemodules.q4server as q4server
import gamemodules.sampserver as sampserver


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


def test_mtaserver_configure_sets_defaults(tmp_path):
    server = DummyServer("mta")

    mtaserver.configure(server, ask=False, port=22003, dir=str(tmp_path), url="http://example.com/mta.tar.gz")

    assert server.data["download_name"] == "mta.tar.gz"


def test_sampserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("samp")
    exe = tmp_path / "samp03svr"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "samp03svr"})

    cmd, cwd = sampserver.get_start_command(server)

    assert cmd == ["./samp03svr"]
    assert cwd == server.data["dir"]


def test_q4server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("q4")
    exe = tmp_path / "q4ded.x86"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "q4ded.x86", "fs_game": "q4base", "hostname": "AlphaGSM q4", "port": 28004, "startmap": "q4dm1"})

    cmd, cwd = q4server.get_start_command(server)

    assert cmd[0] == "./q4ded.x86"
    assert "si_name" in cmd
    assert cwd == server.data["dir"]
