import gamemodules.terraria.common as terraria_common
import gamemodules.terraria.tshock as tshock
import gamemodules.terraria.vanilla as vanilla


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


def test_resolve_terraria_download_uses_explicit_version():
    version, url = terraria_common.resolve_terraria_download("1.4.5.3")

    assert version == "1.4.5.3"
    assert url.endswith("/terraria-server-1453.zip")


def test_resolve_terraria_download_finds_latest_from_homepage(monkeypatch):
    monkeypatch.setattr(
        terraria_common,
        "_head_ok",
        lambda url: "1457" not in url,
    )

    version, url = terraria_common.resolve_terraria_download()

    assert version == "1.4.5.6"
    assert url.endswith("/terraria-server-1456.zip")


def test_resolve_tshock_download_picks_zip_asset(monkeypatch):
    monkeypatch.setattr(
        terraria_common,
        "_read_json",
        lambda url: {
            "tag_name": "v5.2.3",
            "assets": [
                {"name": "notes.txt", "browser_download_url": "http://invalid"},
                {
                    "name": "TShock-5.2.3-release.zip",
                    "browser_download_url": "http://example.com/tshock.zip",
                },
            ],
        },
    )

    version, url = terraria_common.resolve_tshock_download()

    assert version == "v5.2.3"
    assert url == "http://example.com/tshock.zip"


def test_terraria_vanilla_configure_sets_defaults(tmp_path, monkeypatch):
    server = DummyServer("terra")
    monkeypatch.setattr(
        vanilla, "resolve_terraria_download", lambda version=None: ("1.4.5.6", "http://example.com/terraria.zip")
    )

    args, kwargs = vanilla.configure(server, ask=False, port=7777, dir=str(tmp_path))

    assert args == ()
    assert kwargs == {}
    assert server.data["port"] == 7777
    assert server.data["url"] == "http://example.com/terraria.zip"
    assert server.data["backupfiles"] == ["Worlds", "serverconfig.txt", "banlist.txt"]
    assert server.data["world"] == "terra.wld"
    assert server.data["exe_name"] == "Linux/TerrariaServer.bin.x86_64"


def test_tshock_configure_sets_dotnet_defaults(tmp_path, monkeypatch):
    server = DummyServer("shock")
    monkeypatch.setattr(
        tshock, "resolve_tshock_download", lambda: ("v5.2.3", "http://example.com/tshock.zip")
    )

    tshock.configure(server, ask=False, port=7778, dir=str(tmp_path))

    assert server.data["port"] == 7778
    assert server.data["url"] == "http://example.com/tshock.zip"
    assert server.data["dotnetpath"] == "dotnet"
    assert server.data["backupfiles"] == ["Worlds", "serverconfig.txt", "tshock"]


def test_terraria_install_archive_copies_downloaded_tree(tmp_path, monkeypatch):
    server = DummyServer("terra")
    server.data.update(
        {
            "dir": str(tmp_path / "server"),
            "exe_name": "Linux/TerrariaServer.bin.x86_64",
            "url": "http://example.com/terraria.zip",
            "download_name": "terraria-server.zip",
        }
    )
    download_root = tmp_path / "download"
    extracted_root = download_root / "1400"
    executable = extracted_root / "Linux" / "TerrariaServer.bin.x86_64"
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    monkeypatch.setattr(terraria_common.downloader, "getpath", lambda module, args: str(download_root))

    terraria_common.install_archive(server)

    assert (tmp_path / "server" / "Linux" / "TerrariaServer.bin.x86_64").exists()
    assert server.data["current_url"] == "http://example.com/terraria.zip"


def test_terraria_vanilla_start_command_autocreates_missing_world(tmp_path):
    server = DummyServer("terra")
    exe_path = tmp_path / "Linux" / "TerrariaServer.bin.x86_64"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "Linux/TerrariaServer.bin.x86_64",
            "port": 7777,
            "maxplayers": "8",
            "worldname": "terra",
            "world": "terra.wld",
            "worldsize": "2",
        }
    )

    cmd, cwd = vanilla.get_start_command(server)

    assert cmd[0] == "./Linux/TerrariaServer.bin.x86_64"
    assert "-autocreate" in cmd
    assert "2" in cmd
    assert cwd == str(tmp_path)


def test_tshock_start_command_uses_dotnet(tmp_path):
    server = DummyServer("shock")
    dll_path = tmp_path / "TShock.Server.dll"
    dll_path.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "TShock.Server.dll",
            "dotnetpath": "/usr/bin/dotnet",
            "port": 7777,
        }
    )

    cmd, cwd = tshock.get_start_command(server)

    assert cmd == ["/usr/bin/dotnet", "TShock.Server.dll", "-port", "7777"]
    assert cwd == str(tmp_path)
