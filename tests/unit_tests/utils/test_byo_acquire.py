"""Synthetic authenticated acquisition; no real Steam session or network."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from server import ServerError


def acquisition():
    from utils import byo_acquire
    return byo_acquire


def recipe():
    return {"module": "fixture", "managed_import": True, "roots": [""],
            "target": "", "required": ["baseq3/pak0.pk3"],
            "include": ["baseq3/pak*.pk3"],
            "requirements": [{"path": "baseq3/pak0.pk3", "kind": "file"}],
            "sources": [{"id": "steam-owned", "kind": "steamcmd", "app_id": 2200,
                         "platform": "windows", "authentication": "required",
                         "instructions": "Use an entitled account"}]}


def test_acquire_selects_profile_and_publishes_only_allowlisted_files(tmp_path, monkeypatch):
    module = acquisition()
    staging_paths = []
    calls = []
    def download(path, app, anonymous, **kwargs):
        staging = Path(path)
        staging_paths.append(staging)
        calls.append((app, anonymous, kwargs))
        (staging / "baseq3").mkdir()
        (staging / "baseq3/pak0.pk3").write_bytes(b"owned-data")
        (staging / "unrelated-password.txt").write_text("must not be copied")
    monkeypatch.setattr(module.steamcmd, "download", download)
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path / "server")})
    report = module.acquire(server, recipe(), "steam-owned", auth_profile="personal")
    assert calls == [(2200, False, {"force_platform": "windows", "beta_branch": None, "auth_profile": "personal"})]
    assert (tmp_path / "server/baseq3/pak0.pk3").read_bytes() == b"owned-data"
    assert not (tmp_path / "server/unrelated-password.txt").exists()
    assert all(not path.exists() for path in staging_paths)
    assert report["source"] == "steam-owned"
    assert report["game_readiness"] == "not-checked"


def test_authentication_is_required_before_downloading(tmp_path, monkeypatch):
    module = acquisition()
    monkeypatch.setattr(module.steamcmd, "download", lambda *a, **k: pytest.fail("must not download"))
    with pytest.raises(ServerError, match="auth-profile"):
        module.acquire(SimpleNamespace(data={"dir": str(tmp_path)}), recipe(), "steam-owned")


def test_download_failure_removes_staging_without_changing_target(tmp_path, monkeypatch):
    module = acquisition()
    staging_paths = []
    def download(path, *args, **kwargs):
        staging_paths.append(Path(path))
        raise RuntimeError("synthetic download failure")
    monkeypatch.setattr(module.steamcmd, "download", download)
    with pytest.raises(ServerError, match="acquisition failed"):
        module.acquire(SimpleNamespace(data={"dir": str(tmp_path / "server")}), recipe(), "steam-owned", auth_profile="test")
    assert all(not path.exists() for path in staging_paths)
    assert not (tmp_path / "server").exists()


def test_incomplete_download_does_not_publish_any_files(tmp_path, monkeypatch):
    module = acquisition()
    monkeypatch.setattr(module.steamcmd, "download", lambda *args, **kwargs: None)
    with pytest.raises(ServerError, match="required"):
        module.acquire(SimpleNamespace(data={"dir": str(tmp_path / "server")}), recipe(), "steam-owned", auth_profile="test")
    assert not (tmp_path / "server").exists()


def test_unknown_manual_and_unsupported_recipes_do_not_download(tmp_path, monkeypatch):
    module = acquisition()
    monkeypatch.setattr(module.steamcmd, "download", lambda *a, **k: pytest.fail("must not download"))
    server = SimpleNamespace(data={"dir": str(tmp_path)})
    with pytest.raises(ServerError, match="source"):
        module.acquire(server, recipe(), "missing", auth_profile="test")
    manual = recipe()
    manual["managed_import"] = False
    with pytest.raises(ServerError, match="manual"):
        module.acquire(server, manual, "steam-owned", auth_profile="test")


@pytest.mark.parametrize("field,value", [("app_id", "+quit"), ("platform", "other"), ("branch", "main +quit")])
def test_invalid_steam_metadata_is_rejected_before_downloading(tmp_path, monkeypatch, field, value):
    module = acquisition()
    monkeypatch.setattr(module.steamcmd, "download", lambda *a, **k: pytest.fail("must not download"))
    definition = recipe()
    definition["sources"][0][field] = value
    with pytest.raises(ServerError, match="SteamCMD"):
        module.acquire(SimpleNamespace(data={"dir": str(tmp_path)}), definition, "steam-owned", auth_profile="test")
