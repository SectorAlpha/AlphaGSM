from types import SimpleNamespace

import pytest

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
