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


def test_resolve_direct_url_entry_accepts_http_plugin_url():
    resolved = providers_module.resolve_direct_url_entry(
        "https://plugins.example.invalid/TestPlugin.jar",
        allowed_suffixes={".jar": "jar"},
        entry_label="Proxy mod url entries",
        filename_description="a plugin .jar filename",
    )

    assert resolved["requested_id"] == "https://plugins.example.invalid/TestPlugin.jar"
    assert resolved["filename"] == "TestPlugin.jar"
    assert resolved["allowed_host"] == "plugins.example.invalid"
    assert resolved["archive_type"] == "jar"


def test_resolve_direct_url_entry_rejects_bad_scheme():
    with pytest.raises(ServerError, match="http or https URL"):
        providers_module.resolve_direct_url_entry(
            "ftp://plugins.example.invalid/TestPlugin.jar",
            allowed_suffixes={".jar": "jar"},
            entry_label="Proxy mod url entries",
            filename_description="a plugin .jar filename",
        )


def test_resolve_direct_url_entry_rejects_unapproved_filename():
    with pytest.raises(ServerError, match="plugin .jar filename"):
        providers_module.resolve_direct_url_entry(
            "https://plugins.example.invalid/download",
            allowed_suffixes={".jar": "jar"},
            entry_label="Proxy mod url entries",
            filename_description="a plugin .jar filename",
        )


class _Headers:
    def get_content_charset(self):
        return "utf-8"


def test_resolve_mta_community_entry_uses_latest_download_flow(monkeypatch):
    responses = iter(
        [
            """
            <html>
              <body>
                <a href="?p=resources&amp;s=download&amp;resource=19052&amp;selectincludes=1">Download latest version</a>
              </body>
            </html>
            """,
            """
            <html>
              <body>
                The download should start shortly...
                <a href="modules/resources/doDownload.php?file=fps_by_districtzero_1.0.0.zip&amp;name=fps_by_districtzero.zip">here</a>
              </body>
            </html>
            """,
        ]
    )

    class Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return next(responses).encode("utf-8")

    monkeypatch.setattr(providers_module, "urlopen", lambda request, timeout: Response())

    resolved = providers_module.resolve_mta_community_entry(
        "https://community.multitheftauto.com/?p=resources&s=details&id=19052"
    )

    assert resolved["requested_id"] == "https://community.multitheftauto.com/index.php?p=resources&s=details&id=19052"
    assert resolved["resolved_id"] == "mtacommunity.19052.fps_by_districtzero_1.0.0"
    assert resolved["download_page_url"] == (
        "https://community.multitheftauto.com/index.php?p=resources&s=download&resource=19052&selectincludes=1"
    )
    assert resolved["asset_path"] == (
        "modules/resources/doDownload.php?file=fps_by_districtzero_1.0.0.zip&name=fps_by_districtzero.zip"
    )
    assert resolved["filename"] == "fps_by_districtzero.zip"
    assert resolved["archive_type"] == "zip"
    assert resolved["resource_name"] == "fps_by_districtzero"


def test_resolve_mta_community_entry_rejects_non_canonical_page_url():
    with pytest.raises(ServerError, match="canonical resource detail page URL"):
        providers_module.resolve_mta_community_entry(
            "https://community.multitheftauto.com/index.php?p=resources&s=download&resource=19052"
        )


def test_resolve_moddb_entry_uses_downloads_start_link(monkeypatch):
    payload = """
    <html>
      <body>
        <div>Filename</div>
        <div>CAGE8.zip</div>
        <a href="https://www.moddb.com/downloads/start/308604">Download Now</a>
      </body>
    </html>
    """

    class Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return payload.encode("utf-8")

    monkeypatch.setattr(providers_module, "urlopen", lambda request, timeout: Response())

    resolved = providers_module.resolve_moddb_entry(
        "https://www.moddb.com/mods/cage-eight/downloads/cage-eight"
    )

    assert resolved["requested_id"] == "https://www.moddb.com/mods/cage-eight/downloads/cage-eight"
    assert resolved["resolved_id"] == "moddb.downloads.308604"
    assert resolved["download_url"] == "https://www.moddb.com/downloads/start/308604"
    assert resolved["filename"] == "CAGE8.zip"
    assert resolved["archive_type"] == "zip"


def test_resolve_moddb_entry_uses_addons_start_link(monkeypatch):
    payload = """
    <html>
      <body>
        <div>Filename</div>
        <div>z_zm134_minigun.tar.gz</div>
        <a href="https://www.moddb.com/addons/start/308655">Download Now</a>
      </body>
    </html>
    """

    class Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return payload.encode("utf-8")

    monkeypatch.setattr(providers_module, "urlopen", lambda request, timeout: Response())

    resolved = providers_module.resolve_moddb_entry(
        "https://www.moddb.com/games/return-to-castle-wolfenstein/addons/m134-minigun1"
    )

    assert resolved["resolved_id"] == "moddb.addons.308655"
    assert resolved["download_url"] == "https://www.moddb.com/addons/start/308655"
    assert resolved["archive_type"] == "tar"


def test_resolve_moddb_entry_rejects_non_canonical_page_url():
    with pytest.raises(ServerError, match="canonical mod or addon page URL"):
        providers_module.resolve_moddb_entry("https://www.moddb.com/downloads/start/308604")


def test_resolve_moddb_entry_accepts_7z_archive(monkeypatch):
    payload = """
    <html>
      <body>
        <div>Filename</div>
        <div>z_zm134_minigun.7z</div>
        <a href="https://www.moddb.com/addons/start/308655">Download Now</a>
      </body>
    </html>
    """

    class Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return payload.encode("utf-8")

    monkeypatch.setattr(providers_module, "urlopen", lambda request, timeout: Response())

    resolved = providers_module.resolve_moddb_entry(
        "https://www.moddb.com/games/return-to-castle-wolfenstein/addons/m134-minigun1"
    )

    assert resolved["archive_type"] == "7z"
    assert resolved["download_url"] == "https://www.moddb.com/addons/start/308655"


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