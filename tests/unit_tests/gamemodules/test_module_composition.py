from types import SimpleNamespace

import pytest

import gamemodules.hl2dmserver as hl2dm
import gamemodules.palworld as palworld
import gamemodules.palworld.main as palworld_main
from server.module_contract import validate_module_contract


def test_palworld_failed_download_does_not_prepare_settings(tmp_path, monkeypatch):
    server = SimpleNamespace(data={"dir": str(tmp_path)})
    (tmp_path / "DefaultPalWorldSettings.ini").write_text("Default")

    def fail_download(*_args, **_kwargs):
        raise RuntimeError("download failed")

    monkeypatch.setattr(palworld.steamcmd, "download", fail_download)
    with pytest.raises(RuntimeError, match="download failed"):
        palworld.install(server)
    assert not (tmp_path / "Pal/Saved/Config/LinuxServer/PalWorldSettings.ini").exists()


def test_palworld_public_surface_satisfies_contract():
    assert palworld is palworld_main
    assert palworld.module_contract_version == 1
    validate_module_contract("palworld", palworld)


def test_hl2dm_public_surface_satisfies_contract():
    assert hl2dm.module_contract_version == 1
    validate_module_contract("hl2dmserver", hl2dm)


@pytest.mark.parametrize("name", ("palworld", "hl2dmserver"))
def test_loader_accepts_versioned_pilots(name):
    from server import server as server_module

    resolved, module = server_module.find_module(name)
    assert resolved == name
    assert module.module_contract_version == 1
    validate_module_contract(resolved, module)


@pytest.mark.parametrize("name", ("minecraft.vanilla", "teamfortress2"))
def test_loader_keeps_unversioned_regression_modules(name):
    from server import server as server_module

    resolved, module = server_module.find_module(name)
    assert resolved == name
    assert getattr(module, "module_contract_version", None) is None


def test_hl2dm_runtime_wrappers_share_the_declared_ports(monkeypatch):
    import server.runtime as runtime_module

    server = SimpleNamespace(data={})
    calls = []

    def capture(_server, **kwargs):
        calls.append(kwargs)
        return {}

    monkeypatch.setattr(runtime_module, "build_runtime_requirements", capture)
    monkeypatch.setattr(runtime_module, "build_container_spec", capture)
    hl2dm.get_runtime_requirements(server)
    hl2dm.get_container_spec(server)
    assert [call["family"] for call in calls] == ["steamcmd-linux"] * 2
    assert calls[0]["port_definitions"] == calls[1]["port_definitions"]
    assert [(item["key"], item["protocol"]) for item in calls[0]["port_definitions"]] == [
        ("port", "udp"), ("port", "tcp"),
        ("clientport", "udp"), ("sourcetvport", "udp"),
    ]
    assert calls[0]["family"] == hl2dm.RUNTIME_FAMILY
    assert calls[0]["port_definitions"] == hl2dm.PORT_DEFINITIONS
