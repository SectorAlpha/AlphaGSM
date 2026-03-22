import gamemodules.kerbalspaceprogramserver as kerbalspaceprogramserver


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


def test_ksp_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("ksp")
    exe = tmp_path / "Server"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "Server", "port": 8800})

    cmd, cwd = kerbalspaceprogramserver.get_start_command(server)

    assert cmd == ["./Server", "--port", "8800"]
    assert cwd == server.data["dir"]


def test_ksp_configure_stores_url_and_defaults(tmp_path):
    server = DummyServer("ksp")

    kerbalspaceprogramserver.configure(
        server,
        ask=False,
        port=8800,
        dir=str(tmp_path),
        url="https://example.com/LunaMultiplayer-Server-Release.zip",
        download_name="LunaMultiplayer-Server-Release.zip",
    )

    assert server.data["port"] == 8800
    assert server.data["url"] == "https://example.com/LunaMultiplayer-Server-Release.zip"
    assert server.data["download_name"] == "LunaMultiplayer-Server-Release.zip"
    assert server.data["exe_name"] == "Server"


def test_ksp_configure_resolves_default_download(monkeypatch, tmp_path):
    server = DummyServer("ksp")
    monkeypatch.setattr(
        kerbalspaceprogramserver,
        "resolve_download",
        lambda: ("0.29.0", "https://example.com/LunaMultiplayer-Server-Release.zip"),
    )

    kerbalspaceprogramserver.configure(server, ask=False, port=8800, dir=str(tmp_path))

    assert server.data["url"] == "https://example.com/LunaMultiplayer-Server-Release.zip"
    assert server.data["download_name"] == "LunaMultiplayer-Server-Release.zip"
