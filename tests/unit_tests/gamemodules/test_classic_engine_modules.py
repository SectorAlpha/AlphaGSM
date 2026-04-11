import gamemodules.jk2server as jk2server
import gamemodules.q2server as q2server
import gamemodules.qwserver as qwserver
import gamemodules.rtcwserver as rtcwserver
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


def test_q2server_runtime_requirements_use_quake_linux_family(tmp_path):
    (tmp_path / "q2ded").write_text("")
    server = DummyServer("q2")
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

    requirements = q2server.get_runtime_requirements(server)
    spec = q2server.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "quake-linux"
    assert requirements["ports"] == [
        {"host": 27910, "container": 27910, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./q2ded"


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


def test_qwserver_runtime_requirements_use_quake_linux_family(tmp_path):
    (tmp_path / "mvdsv").write_text("")
    server = DummyServer("qw")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "mvdsv",
            "hostname": "AlphaGSM qw",
            "port": 27500,
            "startmap": "dm2",
        }
    )

    requirements = qwserver.get_runtime_requirements(server)
    spec = qwserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "quake-linux"
    assert requirements["ports"] == [
        {"host": 27500, "container": 27500, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./mvdsv"


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


def test_rtcwserver_runtime_requirements_use_quake_linux_family(tmp_path):
    (tmp_path / "iowolfded.x86_64").write_text("")
    server = DummyServer("rtcw")
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

    requirements = rtcwserver.get_runtime_requirements(server)
    spec = rtcwserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "quake-linux"
    assert requirements["ports"] == [
        {"host": 27960, "container": 27960, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./iowolfded.x86_64"


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


def test_jk2server_runtime_requirements_use_quake_linux_family(tmp_path):
    (tmp_path / "jk2mvded.x86_64").write_text("")
    server = DummyServer("jk2")
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

    requirements = jk2server.get_runtime_requirements(server)
    spec = jk2server.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "quake-linux"
    assert requirements["ports"] == [
        {"host": 28070, "container": 28070, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./jk2mvded.x86_64"


def test_etlegacyserver_runtime_requirements_use_quake_linux_family(tmp_path):
    (tmp_path / "etl.x86_64").write_text("")
    server = DummyServer("etl")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "etl.x86_64",
            "fs_game": "legacy",
            "hostname": "AlphaGSM etl",
            "port": 27960,
            "configfile": "etl_server.cfg",
        }
    )

    requirements = etlegacyserver.get_runtime_requirements(server)
    spec = etlegacyserver.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "quake-linux"
    assert requirements["ports"] == [
        {"host": 27960, "container": 27960, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./etl.x86_64"
