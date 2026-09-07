"""Docker identity contracts for servers that reject root in CI."""

from importlib import import_module
from pathlib import Path

import pytest

import server.runtime as runtime_module
from tests.unit_tests.gamemodules.helpers import DummyServer


@pytest.mark.parametrize("module_name", [
    "dayofdragonsserver",
    "exfilserver",
    "frozenflameserver",
    "hcuserver",
    "inssserver",
    "memoriesofmarsserver",
    "mordserver",
    "satisfactory",
    "sbotsserver",
    "smallandserver",
    "squad44server",
    "tuserver",
])
def test_root_rejecting_servers_declare_matching_host_user_hooks(module_name, tmp_path, monkeypatch):
    module = import_module("gamemodules." + module_name)
    manager_root = tmp_path / "manager"
    monkeypatch.setenv("ALPHAGSM_HOME", str(manager_root))
    steamcmd_root = tmp_path / "Steam"
    for architecture in ("linux32", "linux64"):
        sdk_root = steamcmd_root / architecture
        sdk_root.mkdir(parents=True)
        (sdk_root / "steamclient.so").write_bytes(b"mock Steam SDK")
    monkeypatch.setattr(runtime_module.steamcmd_module, "STEAMCMD_DIR", str(steamcmd_root))
    server = DummyServer(name=module_name)
    install_dir = tmp_path / "server"
    install_dir.mkdir()
    module.configure(server, False, port=7777, dir=str(install_dir))
    executable = Path(server.data["dir"]) / server.data["exe_name"]
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(b"mock executable")
    process_command, process_cwd = module.get_start_command(server)

    requirements = module.get_runtime_requirements(server)
    spec = module.get_container_spec(server)

    assert requirements["family"] == "steamcmd-linux"
    assert requirements["engine"] == "docker"
    expected_home = "/home/alphagsm"
    for hook_result in (requirements, spec):
        assert hook_result.get("run_as_host_user") is True
        assert hook_result["container_home"] == expected_home
        assert hook_result["env"]["HOME"] == expected_home
        assert {
            "source": str(manager_root / "runtime" / module_name / "home"),
            "target": expected_home,
            "mode": "rw",
        } in hook_result["mounts"]
        assert {
            "source": server.data["dir"], "target": "/srv/server", "mode": "rw",
        } in hook_result["mounts"]
        for bits in ("32", "64"):
            for target in (f".steam/sdk{bits}", f".steam/steamcmd/linux{bits}"):
                assert {
                    "source": str(steamcmd_root / f"linux{bits}"),
                    "target": f"{expected_home}/{target}",
                    "mode": "ro",
                } in hook_result["mounts"]
        assert not any(mount["target"].startswith("/root") for mount in hook_result["mounts"])
    assert spec["ports"] == requirements["ports"]
    assert spec["command"] == process_command
    assert spec["working_dir"] == "/srv/server"
    assert Path(process_cwd) == install_dir
    assert module.get_start_command(server) == (process_command, process_cwd)
