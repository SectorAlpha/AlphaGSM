"""Synthetic authenticated acquisition; no real Steam session or network."""

from pathlib import Path
from types import SimpleNamespace
import zipfile

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


@pytest.mark.parametrize("directory,filename", [("baseq3", "pak0.pk3"), ("BaseQ3", "PAK0.PK3")])
def test_acquire_selects_profile_and_publishes_only_allowlisted_files(tmp_path, monkeypatch, directory, filename):
    module = acquisition()
    staging_paths = []
    calls = []
    def download(path, app, anonymous, **kwargs):
        staging = Path(path)
        staging_paths.append(staging)
        calls.append((app, anonymous, kwargs))
        (staging / directory).mkdir()
        (staging / directory / filename).write_bytes(b"owned-data")
        (staging / "unrelated-password.txt").write_text("must not be copied")
    monkeypatch.setattr(module.steamcmd, "download", download)
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path / "server")})
    report = module.acquire(server, dict(recipe(), case_insensitive=True), "steam-owned", auth_profile="personal")
    assert calls == [(2200, False, {"force_platform": "windows", "beta_branch": None, "auth_profile": "personal"})]
    assert (tmp_path / "server/baseq3/pak0.pk3").read_bytes() == b"owned-data"
    assert not (tmp_path / "server/unrelated-password.txt").exists()
    assert all(not path.exists() for path in staging_paths)
    assert report["source"] == "steam-owned"
    assert report["game_readiness"] == "not-checked"


def test_additional_app_ids_merge_before_the_allowlist(tmp_path, monkeypatch):
    module = acquisition()
    calls = []

    def download(path, app, anonymous, **kwargs):
        calls.append(app)
        root = Path(path)
        if app == 2200:
            (root / "baseq3").mkdir()
            (root / "baseq3" / "pak0.pk3").write_bytes(b"base")
            (root / "steamapps").mkdir()
            (root / "steamapps" / "secret.txt").write_text("must not be copied")
        elif app == 2201:
            (root / "uo").mkdir()
            (root / "uo" / "pak0.pk3").write_bytes(b"expansion")
            (root / "CoDUO.exe").write_bytes(b"client")
        else:
            raise AssertionError(app)

    monkeypatch.setattr(module.steamcmd, "download", download)
    definition = recipe()
    definition["sources"][0]["additional_app_ids"] = [2201]
    definition["include"] = ["baseq3/pak*.pk3", "uo/pak*.pk3"]
    definition["required"] = ["baseq3/pak0.pk3", "uo/pak0.pk3"]
    definition["requirements"] = [
        {"path": "baseq3/pak0.pk3", "kind": "file"},
        {"path": "uo/pak0.pk3", "kind": "file"},
    ]
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path / "server")})

    module.acquire(server, definition, "steam-owned", auth_profile="personal")

    assert calls == [2200, 2201]
    assert (tmp_path / "server/baseq3/pak0.pk3").read_bytes() == b"base"
    assert (tmp_path / "server/uo/pak0.pk3").read_bytes() == b"expansion"
    assert not (tmp_path / "server/CoDUO.exe").exists()
    assert not (tmp_path / "server/steamapps").exists()


def test_acquire_rejects_publication_that_drops_a_multiplayer_map(tmp_path, monkeypatch):
    """A dedicated build must keep every multiplayer map from the owned source."""

    module = acquisition()

    def download(path, app, anonymous, **kwargs):
        root = Path(path)
        (root / "main").mkdir()
        with zipfile.ZipFile(root / "main" / "pak0.pk3", "w") as bundle:
            bundle.writestr("maps/mp/mp_carentan.bsp", b"map")
            bundle.writestr("maps/brecourt.bsp", b"campaign")
        with zipfile.ZipFile(root / "main" / "extra.pk3", "w") as bundle:
            bundle.writestr("maps/mp/mp_ship.bsp", b"map")
            bundle.writestr("maps/bastogne1.bsp", b"campaign")

    monkeypatch.setattr(module.steamcmd, "download", download)
    definition = recipe()
    definition["include"] = ["main/pak0.pk3"]
    definition["required"] = ["main/pak0.pk3"]
    definition["requirements"] = [{"path": "main/pak0.pk3", "kind": "file"}]
    server = SimpleNamespace(name="test", data={"dir": str(tmp_path / "server")})

    with pytest.raises(ServerError, match="mp_ship"):
        module.acquire(server, definition, "steam-owned", auth_profile="personal")

    assert not (tmp_path / "server" / "main" / "extra.pk3").exists()


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
