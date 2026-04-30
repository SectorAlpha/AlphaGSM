import json
from urllib.error import URLError

import pytest

from server import ServerError
from server.modsupport.errors import ModSupportError
from server.modsupport import providers as providers_module


def test_validate_gamebanana_id_accepts_numeric_string():
    assert providers_module.validate_gamebanana_id("12345") == "12345"


def test_validate_gamebanana_id_rejects_non_numeric_value():
    with pytest.raises(ServerError, match="numeric item id"):
        providers_module.validate_gamebanana_id("mod_bad")


def test_validate_workshop_id_accepts_numeric_string():
    assert providers_module.validate_workshop_id("98765") == "98765"


def test_validate_workshop_id_rejects_non_numeric_value():
    with pytest.raises(ServerError, match="numeric workshop id"):
        providers_module.validate_workshop_id("map_bad")


def test_resolve_gamebanana_mod_chooses_latest_supported_clean_archive(monkeypatch):
    payload = {
        "_aFiles": [
            {
                "_idRow": 1,
                "_sFile": "ignore.exe",
                "_bHasContents": True,
                "_bIsArchived": False,
                "_sAvResult": "ok",
                "_tsDateAdded": 10,
            },
            {
                "_idRow": 2,
                "_sFile": "older.zip",
                "_bHasContents": True,
                "_bIsArchived": False,
                "_sAvResult": "ok",
                "_sDownloadUrl": "https://gamebanana.com/dl/2",
                "_tsDateAdded": 20,
            },
            {
                "_idRow": 3,
                "_sFile": "infected.zip",
                "_bHasContents": True,
                "_bIsArchived": False,
                "_sAvResult": "infected",
                "_sDownloadUrl": "https://gamebanana.com/dl/3",
                "_tsDateAdded": 30,
            },
            {
                "_idRow": 4,
                "_sFile": "latest.tar.gz",
                "_bHasContents": True,
                "_bIsArchived": False,
                "_sAvResult": "ok",
                "_sDownloadUrl": "https://gamebanana.com/dl/4",
                "_tsDateAdded": 40,
            },
        ]
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(providers_module, "urlopen", lambda request, timeout: Response())

    resolved = providers_module.resolve_gamebanana_mod("12345")

    assert resolved["requested_id"] == "12345"
    assert resolved["resolved_id"] == "gamebanana.12345.4"
    assert resolved["download_url"] == "https://gamebanana.com/dl/4"
    assert resolved["archive_type"] == "tar"


def test_resolve_gamebanana_mod_normalizes_fetch_failures(monkeypatch):
    monkeypatch.setattr(
        providers_module,
        "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("down")),
    )

    with pytest.raises(ModSupportError, match="Failed to query GameBanana item '12345'"):
        providers_module.resolve_gamebanana_mod("12345")


def test_resolve_gamebanana_mod_rejects_items_without_supported_archives(monkeypatch):
    payload = {
        "_aFiles": [
            {
                "_idRow": 1,
                "_sFile": "readme.txt",
                "_bHasContents": True,
                "_bIsArchived": False,
                "_sAvResult": "ok",
                "_sDownloadUrl": "https://gamebanana.com/dl/1",
                "_tsDateAdded": 10,
            }
        ]
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(providers_module, "urlopen", lambda request, timeout: Response())

    with pytest.raises(ModSupportError, match="does not expose a supported zip or tar archive"):
        providers_module.resolve_gamebanana_mod("12345")