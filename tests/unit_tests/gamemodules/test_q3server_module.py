import gamemodules.q3server as q3server


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


def test_q3server_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("q3")

    q3server.configure(server, ask=False, port=27960, dir=str(tmp_path), url="http://example.com/q3.tar.gz")

    assert server.data["fs_game"] == "baseq3"
    assert server.data["startmap"] == "q3dm17"


def test_q3server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("q3")
    exe = tmp_path / "q3ded.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "q3ded.x86_64",
            "fs_game": "baseq3",
            "hostname": "AlphaGSM q3",
            "port": 27960,
            "startmap": "q3dm17",
        }
    )

    cmd, cwd = q3server.get_start_command(server)

    assert cmd[0] == "./q3ded.x86_64"
    assert "net_port" in cmd
    assert cwd == server.data["dir"]


def test_q3server_runtime_requirements_use_quake_linux_family(tmp_path):
    (tmp_path / "q3ded.x86_64").write_text("")
    server = DummyServer("q3")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "q3ded.x86_64",
            "fs_game": "baseq3",
            "hostname": "AlphaGSM q3",
            "port": 27960,
            "startmap": "q3dm17",
        }
    )

    requirements = q3server.get_runtime_requirements(server)
    spec = q3server.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "quake-linux"
    assert requirements["ports"] == [
        {"host": 27960, "container": 27960, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./q3ded.x86_64"
