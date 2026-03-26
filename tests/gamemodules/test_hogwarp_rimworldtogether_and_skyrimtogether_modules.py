import gamemodules.hogwarpserver as hogwarpserver
import gamemodules.rimworldtogetherserver as rimworldtogetherserver
import gamemodules.skyrimtogetherrebornserver as skyrimtogetherrebornserver


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


def test_hogwarp_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("hogwarp")
    exe = tmp_path / "HogWarpServer.exe"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "HogWarpServer.exe", "port": 7777})

    cmd, cwd = hogwarpserver.get_start_command(server)

    assert cmd == ["./HogWarpServer.exe", "7777"]
    assert cwd == server.data["dir"]


def test_rimworldtogether_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("rw")
    exe = tmp_path / "RimworldTogetherServer.x86_64"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "RimworldTogetherServer.x86_64",
            "port": 25555,
        }
    )

    cmd, cwd = rimworldtogetherserver.get_start_command(server)

    assert cmd == ["./RimworldTogetherServer.x86_64", "--port", "25555"]
    assert cwd == server.data["dir"]


def test_rimworldtogether_configure_resolves_default_download(monkeypatch, tmp_path):
    server = DummyServer("rw")
    monkeypatch.setattr(
        rimworldtogetherserver,
        "resolve_download",
        lambda version=None: ("25.7.11.1", "https://example.com/rimworld-together-server.zip"),
    )

    rimworldtogetherserver.configure(server, ask=False, port=25555, dir=str(tmp_path))

    assert server.data["url"] == "https://example.com/rimworld-together-server.zip"
    assert server.data["download_name"] == "rimworld-together-server.zip"


def test_skyrimtogether_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("str")
    exe = tmp_path / "SkyrimTogetherServer"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "SkyrimTogetherServer", "port": 10578})

    cmd, cwd = skyrimtogetherrebornserver.get_start_command(server)

    assert cmd == ["./SkyrimTogetherServer", "--port", "10578"]
    assert cwd == server.data["dir"]
