import gamemodules.subnauticaserver as subnauticaserver


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


def test_subnautica_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("subnautica")
    exe = tmp_path / "NitroxServer"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "NitroxServer", "port": 11000})

    cmd, cwd = subnauticaserver.get_start_command(server)

    assert cmd == ["./NitroxServer", "--port", "11000"]
    assert cwd == server.data["dir"]


def test_subnautica_configure_stores_url_and_defaults(tmp_path):
    server = DummyServer("subnautica")

    subnauticaserver.configure(
        server,
        ask=False,
        port=11000,
        dir=str(tmp_path),
        url="https://example.com/nitrox.zip",
        download_name="nitrox.zip",
    )

    assert server.data["port"] == 11000
    assert server.data["url"] == "https://example.com/nitrox.zip"
    assert server.data["download_name"] == "nitrox.zip"
    assert server.data["exe_name"] == "NitroxServer"


def test_subnautica_configure_resolves_default_download(monkeypatch, tmp_path):
    server = DummyServer("subnautica")
    monkeypatch.setattr(
        subnauticaserver,
        "resolve_download",
        lambda version=None: ("1.0.0", "https://example.com/nitrox-server-linux.zip"),
    )

    subnauticaserver.configure(server, ask=False, port=11000, dir=str(tmp_path))

    assert server.data["url"] == "https://example.com/nitrox-server-linux.zip"
    assert server.data["download_name"] == "nitrox-server-linux.zip"
