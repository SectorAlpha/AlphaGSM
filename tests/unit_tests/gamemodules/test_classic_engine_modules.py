import gamemodules.jk2server as jk2server
import gamemodules.q2server as q2server
import gamemodules.qwserver as qwserver
import gamemodules.rtcwserver as rtcwserver


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


def test_q2server_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("q2")

    q2server.configure(server, ask=False, port=27910, dir=str(tmp_path), url="http://example.com/q2.tar.gz")

    assert server.data["gamedir"] == "baseq2"
    assert server.data["startmap"] == "q2dm1"


def test_q2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("q2")
    exe = tmp_path / "q2ded"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "q2ded",
            "gamedir": "baseq2",
            "hostname": "AlphaGSM q2",
            "port": 27910,
            "startmap": "q2dm1",
        }
    )

    cmd, cwd = q2server.get_start_command(server)

    assert cmd[0] == "./q2ded"
    assert "+map" in cmd
    assert cwd == server.data["dir"]


def test_qwserver_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("qw")

    qwserver.configure(server, ask=False, port=27500, dir=str(tmp_path), url="http://example.com/qw.tar.gz")

    assert server.data["startmap"] == "dm2"


def test_qwserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("qw")
    exe = tmp_path / "mvdsv"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "mvdsv",
            "hostname": "AlphaGSM qw",
            "port": 27500,
            "startmap": "dm2",
        }
    )

    cmd, cwd = qwserver.get_start_command(server)

    assert cmd == ["./mvdsv", "-port", "27500", "+hostname", "AlphaGSM qw", "+map", "dm2"]
    assert cwd == server.data["dir"]


def test_rtcwserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("rtcw")
    exe = tmp_path / "iowolfded.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "iowolfded.x86_64",
            "fs_game": "main",
            "hostname": "AlphaGSM rtcw",
            "port": 27960,
            "startmap": "mp_beach",
        }
    )

    cmd, cwd = rtcwserver.get_start_command(server)

    assert cmd[0] == "./iowolfded.x86_64"
    assert "sv_hostname" in cmd
    assert cwd == server.data["dir"]


def test_jk2server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("jk2")
    exe = tmp_path / "jk2mvded.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "jk2mvded.x86_64",
            "fs_game": "base",
            "hostname": "AlphaGSM jk2",
            "port": 28070,
            "startmap": "ffa_bespin",
        }
    )

    cmd, cwd = jk2server.get_start_command(server)

    assert cmd[0] == "./jk2mvded.x86_64"
    assert "net_port" in cmd
    assert cwd == server.data["dir"]
