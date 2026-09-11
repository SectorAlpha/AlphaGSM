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
    assert server.data["exe_name"] == "VintagestoryServer.dll"
    assert server.data["dotnetpath"] == "dotnet"


def test_vintagestoryserver_resolve_download_uses_latest_linuxserver(monkeypatch):
    monkeypatch.setattr(
        vintagestoryserver,
        "_read_json",
        lambda url: {
            "1.22.1": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.22.1.tar.gz",
                    "urls": {"cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.22.1.tar.gz"},
                }
            },
            "1.22.2": {
                "linuxserver": {
                    "filename": "vs_server_linux-x64_1.22.2.tar.gz",
                    "urls": {"cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.22.2.tar.gz"},
                    "latest": 1,
                }
            },
        },
    )

    version, url = vintagestoryserver.resolve_download("latest")

    assert version == "1.22.2"
    assert url.endswith("vs_server_linux-x64_1.22.2.tar.gz")


def test_vintagestoryserver_configure_auto_resolves_latest(tmp_path, monkeypatch):
    server = DummyServer("vs")
    monkeypatch.setattr(
        vintagestoryserver,
        "resolve_download",
        lambda version=None: ("1.22.2", "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.22.2.tar.gz"),
    )

    vintagestoryserver.configure(server, ask=False, port=42420, dir=str(tmp_path))

    assert server.data["version"] == "1.22.2"
    assert server.data["url"].endswith("vs_server_linux-x64_1.22.2.tar.gz")
    assert server.data["download_name"] == "vs_server_linux-x64_1.22.2.tar.gz"


def test_vintagestoryserver_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("vs")
    exe = tmp_path / "VintagestoryServer.dll"
    exe.write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "VintagestoryServer.dll", "dotnetpath": "/usr/bin/dotnet"})

    cmd, cwd = vintagestoryserver.get_start_command(server)

    assert cmd == ["/usr/bin/dotnet", "VintagestoryServer.dll", "--dataPath", str(tmp_path) + "/"]
    assert cwd == server.data["dir"]


def test_vintagestoryserver_get_start_command_uses_relative_datapath_for_docker(tmp_path):
    server = DummyServer("vs")
    exe = tmp_path / "VintagestoryServer.dll"
    exe.write_text("")
    server.data.update({
        "dir": str(tmp_path) + "/",
        "exe_name": "VintagestoryServer.dll",
        "dotnetpath": "/usr/bin/dotnet",
        "runtime": "docker",
    })

    cmd, cwd = vintagestoryserver.get_start_command(server)

    assert cmd == ["/usr/bin/dotnet", "VintagestoryServer.dll", "--dataPath", "."]
    assert cwd == server.data["dir"]


def test_vintagestoryserver_runtime_requirements_declare_dotnet(tmp_path):
    server = DummyServer("vs")
    (tmp_path / "VintagestoryServer.dll").write_text("")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "VintagestoryServer.dll", "port": 42420, "dotnetpath": "/usr/bin/dotnet"})

    requirements = vintagestoryserver.get_runtime_requirements(server)
    spec = vintagestoryserver.get_container_spec(server)

    assert requirements["host_dependencies"] == (
        {"id": "dotnet", "display_name": ".NET", "command_key": "dotnetpath", "command": "dotnet"},
    )
    assert spec["command"] == ["/usr/bin/dotnet", "VintagestoryServer.dll", "--dataPath", str(tmp_path) + "/"]


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
