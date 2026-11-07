"""Remote SDK diagnostics expose revisions, never complete configuration content."""

import hashlib

from tests.integration_tests.squad44_sdk_diagnostics import collect_sdk_metadata


def test_metadata_reports_distinct_sdk_hashes_and_only_whitelisted_manifest_fields(tmp_path):
    install = tmp_path / "server"
    steamcmd = tmp_path / "steamcmd"
    for root, payload in ((install, b"vendor sdk"), (steamcmd, b"new steamcmd sdk")):
        (root / "linux64").mkdir(parents=True)
        (root / "linux64/steamclient.so").write_bytes(payload)
    (install / "steamapps").mkdir()
    (install / "steamapps/appmanifest_746200.acf").write_text(
        '\"AppState\" { \"buildid\" \"21989442\" \"secret\" \"do-not-print\" '
        '\"InstalledDepots\" { \"1006\" { \"manifest\" \"4559160656493359681\" } } }',
        encoding="utf-8")
    metadata = collect_sdk_metadata(install, steamcmd)
    assert metadata["vendor_sdk"]["sha256"] == hashlib.sha256(b"vendor sdk").hexdigest()
    assert metadata["steamcmd_sdk"]["sha256"] == hashlib.sha256(b"new steamcmd sdk").hexdigest()
    assert metadata["server_manifest"] == {"buildid": "21989442", "sdk_depot_manifest": "4559160656493359681"}
    assert "do-not-print" not in repr(metadata)


def test_missing_or_oversized_metadata_remains_diagnostic_only(tmp_path):
    (tmp_path / "steamapps").mkdir()
    (tmp_path / "steamapps/appmanifest_746200.acf").write_bytes(b"x" * (1024 * 1024 + 1))
    metadata = collect_sdk_metadata(tmp_path, tmp_path / "missing-steamcmd")
    assert metadata["vendor_sdk"]["available"] is False
    assert metadata["steamcmd_sdk"]["available"] is False
    assert metadata["server_manifest"] == {"unavailable": "manifest exceeds 1 MiB"}
