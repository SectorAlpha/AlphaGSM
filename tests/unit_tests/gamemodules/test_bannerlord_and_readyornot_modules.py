import gamemodules.bannerlordserver as bannerlordserver
import gamemodules.readyornotserver as readyornotserver
import server.runtime as runtime_module


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
        self.stop_calls = 0
        self.start_calls = 0

    def stop(self):
        self.stop_calls += 1

    def start(self):
        self.start_calls += 1


def test_bannerlord_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("banner")
    exe = tmp_path / "bin" / "Linux64_Shipping_Server" / "TaleWorlds.Starter.DotNetCore.Linux.dll"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "bin/Linux64_Shipping_Server/TaleWorlds.Starter.DotNetCore.Linux.dll",
            "port": 7210,
            "queryport": 7211,
            "game_type": "Captain",
            "scene": "mp_sergeant_battle",
            "maxplayers": 64,
        }
    )

    cmd, cwd = bannerlordserver.get_start_command(server)

    assert cmd[:2] == ["dotnet", "TaleWorlds.Starter.DotNetCore.Linux.dll"]
    assert "_PORT_7210" in cmd
    assert "_QUERYPORT_7211" in cmd
    assert cwd == str(tmp_path / "bin" / "Linux64_Shipping_Server")


def test_bannerlord_runtime_requirements_declare_dotnet_host_dependency(tmp_path):
    server = DummyServer("banner")
    server.module = bannerlordserver
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 7210,
            "queryport": 7211,
        }
    )

    requirements = runtime_module._get_module_runtime_requirements(server)

    assert requirements["runtime"] == "docker"
    assert requirements["runtime_family"] == "steamcmd-linux"
    assert requirements["host_dependencies"] == [
        {"id": "dotnet", "display_name": ".NET", "kind": "command", "command": "dotnet"}
    ]


def test_bannerlord_container_spec_uses_launch_subdirectory(tmp_path):
    server = DummyServer("banner")
    server.module = bannerlordserver
    exe = tmp_path / "bin" / "Linux64_Shipping_Server" / "TaleWorlds.Starter.DotNetCore.Linux.dll"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "bin/Linux64_Shipping_Server/TaleWorlds.Starter.DotNetCore.Linux.dll",
            "port": 7210,
            "queryport": 7211,
            "game_type": "Captain",
            "scene": "mp_sergeant_battle",
            "maxplayers": 64,
        }
    )

    spec = bannerlordserver.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server/bin/Linux64_Shipping_Server"
    assert spec["command"][:2] == ["dotnet", "TaleWorlds.Starter.DotNetCore.Linux.dll"]


def test_readyornot_get_start_command_builds_expected_args(tmp_path, monkeypatch):
    observed = {}

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        observed["wineprefix"] = wineprefix
        observed["prefer_proton"] = prefer_proton
        return list(cmd)

    monkeypatch.setattr(readyornotserver.proton, "wrap_command", fake_wrap_command)
    monkeypatch.setattr(readyornotserver, "IS_LINUX", True)
    server = DummyServer("ron")
    exe = tmp_path / "ReadyOrNotServer.exe"
    exe.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ReadyOrNotServer.exe",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 16,
        }
    )

    cmd, cwd = readyornotserver.get_start_command(server)

    assert cmd[0] == "ReadyOrNotServer.exe"
    assert "-Port=7777" in cmd
    assert "-QueryPort=27015" in cmd
    assert cwd == str(tmp_path)
    assert observed == {"wineprefix": None, "prefer_proton": False}


def test_bannerlord_and_readyornot_update_downloads_and_optionally_restart(monkeypatch):
    banner = DummyServer("banner")
    banner.data["dir"] = "/srv/banner/"
    ron = DummyServer("ron")
    ron.data["dir"] = "/srv/ron/"
    calls = []

    monkeypatch.setattr(
        bannerlordserver.steamcmd,
        "download",
        lambda path, app_id, anon, validate=True, **kwargs: calls.append((path, app_id, anon, validate, kwargs)),
    )

    bannerlordserver.update(banner, validate=True, restart=True)
    readyornotserver.update(ron, validate=False, restart=False)

    assert ("/srv/banner/", 1863440, False, True, {"beta_branch": bannerlordserver.BANNERLORD_LINUX_BETA_BRANCH}) in calls
    assert ("/srv/ron/", 950290, True, False, {"force_windows": True}) in calls
    assert banner.start_calls == 1
