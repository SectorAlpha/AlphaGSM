import gamemodules.ss14server as ss14server
import gamemodules.vintagestoryserver as vintagestoryserver


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


def test_vintagestoryserver_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("vs")

    vintagestoryserver.configure(
        server,
        ask=False,
        port=42420,
        dir=str(tmp_path),
        url="https://example.com/vs.tar.gz",
    )

    assert server.data["download_name"] == "vs.tar.gz"
    assert server.data["worldname"] == "vs"


def test_vintagestoryserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("vs")
    exe = tmp_path / "VintagestoryServer"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "VintagestoryServer"})

    cmd, cwd = vintagestoryserver.get_start_command(server)

    assert cmd == ["./VintagestoryServer", "--dataPath", str(tmp_path) + "/"]
    assert cwd == server.data["dir"]


def test_ss14server_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("ss14")

    ss14server.configure(
        server,
        ask=False,
        port=1212,
        dir=str(tmp_path),
        url="https://example.com/ss14.zip",
    )

    assert server.data["download_name"] == "ss14.zip"


def test_ss14server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ss14")
    exe = tmp_path / "Robust.Server"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "Robust.Server"})

    cmd, cwd = ss14server.get_start_command(server)

    assert cmd == ["./Robust.Server"]
    assert cwd == server.data["dir"]
