import gamemodules.ts3server as ts3server


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


def test_resolve_teamspeak_download_uses_explicit_version():
    version, url = ts3server.resolve_teamspeak_download("3.13.7")

    assert version == "3.13.7"
    assert url.endswith("/3.13.7/teamspeak3-server_linux_amd64-3.13.7.tar.bz2")


def test_resolve_teamspeak_download_parses_download_page(monkeypatch):
    monkeypatch.setattr(ts3server, "_read_download_page", lambda: "Server 64-bit 3.13.7")

    version, url = ts3server.resolve_teamspeak_download()

    assert version == "3.13.7"
    assert url.endswith("/3.13.7/teamspeak3-server_linux_amd64-3.13.7.tar.bz2")


def test_ts3_configure_sets_defaults(tmp_path):
    server = DummyServer("tsalpha")

    args, kwargs = ts3server.configure(server, ask=False, dir=str(tmp_path), version="3.13.7")

    assert args == ()
    assert kwargs == {}
    assert server.data["port"] == 9987
    assert server.data["queryport"] == "10011"
    assert server.data["filetransferport"] == "30033"
    assert server.data["download_name"] == "teamspeak3-server_linux_amd64-3.13.7.tar.bz2"


def test_ts3_install_extracts_archive(tmp_path, monkeypatch):
    server = DummyServer("tsalpha")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ts3server",
            "url": "http://example.com/ts3.tar.bz2",
            "download_name": "teamspeak3-server_linux_amd64-3.13.7.tar.bz2",
        }
    )
    download_root = tmp_path / "download"
    extracted = download_root / "teamspeak3-server_linux_amd64"
    binary = extracted / "ts3server"
    binary.parent.mkdir(parents=True)
    binary.write_text("")

    monkeypatch.setattr(ts3server.downloader, "getpath", lambda module, args: str(download_root))

    ts3server.install(server)

    assert (tmp_path / "ts3server").exists()
    assert server.data["current_url"] == "http://example.com/ts3.tar.bz2"


def test_ts3_get_start_command_builds_ports(tmp_path):
    server = DummyServer("tsalpha")
    exe = tmp_path / "ts3server"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ts3server",
            "port": 9987,
            "queryport": "10011",
            "filetransferport": "30033",
            "license_accepted": True,
        }
    )

    cmd, cwd = ts3server.get_start_command(server)

    assert cmd[0] == "./ts3server"
    assert "default_voice_port=9987" in cmd
    assert "query_port=10011" in cmd
    assert "filetransfer_port=30033" in cmd
    assert cwd == server.data["dir"]
