"""Restore real steamcmd functions for unit-testing the steamcmd module itself.

The root conftest replaces steamcmd.download / install_steamcmd with no-ops
to prevent real downloads.  Tests in this directory need the actual function
logic (with subprocess / url_download mocked at a lower level).
"""
import pytest
import utils.steamcmd as _sc

_REAL_DOWNLOAD = _sc.download
_REAL_INSTALL = _sc.install_steamcmd
_REAL_AUTOUPDATE = _sc.get_autoupdate_script


@pytest.fixture(autouse=True)
def _restore_steamcmd(monkeypatch):
    """Put back the real steamcmd functions so test_steamcmd.py can test them."""
    monkeypatch.setattr(_sc, "download", _REAL_DOWNLOAD)
    monkeypatch.setattr(_sc, "install_steamcmd", _REAL_INSTALL)
    monkeypatch.setattr(_sc, "get_autoupdate_script", _REAL_AUTOUPDATE)
