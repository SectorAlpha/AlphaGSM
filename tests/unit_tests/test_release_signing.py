"""Release signing fails closed and checksums describe the signed bytes."""
import hashlib
from pathlib import Path

import pytest

from scripts import sign_release


def test_missing_certificate_blocks_release(monkeypatch, tmp_path):
    monkeypatch.delenv("ALPHAGSM_SIGN_PFX", raising=False)
    with pytest.raises(ValueError, match="ALPHAGSM_SIGN_PFX"):
        sign_release.prepare(tmp_path / "signing")


def test_environment_export_rejects_injected_lines(monkeypatch, tmp_path):
    path = tmp_path / "env"
    monkeypatch.setenv("GITHUB_ENV", str(path))
    with pytest.raises(ValueError, match="single-line"):
        sign_release.export("IDENTITY", "name\nUNRELATED=changed")
    assert not path.exists()


def test_signing_errors_do_not_expose_provider_output(monkeypatch):
    class Result:
        returncode = 1
        stdout = "secret-provider-token"
        stderr = "secret-password"

    monkeypatch.setattr(sign_release.subprocess, "run", lambda *args, **kwargs: Result())
    with pytest.raises(RuntimeError) as raised:
        sign_release.run("signer", "secret-password")
    assert "secret" not in str(raised.value)


def test_notarization_must_accept_before_checksum_changes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sign_release.sys, "platform", "darwin")
    for key in ("ARTIFACT_NAME", "ALPHAGSM_APPLE_ID", "ALPHAGSM_APPLE_TEAM_ID", "ALPHAGSM_APPLE_PASSWORD"):
        monkeypatch.setenv(key, "fixture")
    release = tmp_path / "release-artifacts"
    release.mkdir()
    binary = release / "fixture"
    binary.write_bytes(b"signed binary")
    monkeypatch.setattr(sign_release, "run", lambda *args: '{"status":"Invalid"}')
    with pytest.raises(RuntimeError, match="notarization"):
        sign_release.sign(tmp_path)
    assert not (release / "fixture.sha256").exists()
    monkeypatch.setattr(sign_release, "run", lambda *args: '{"status":"Accepted"}')
    sign_release.sign(tmp_path)
    assert (release / "fixture.sha256").read_text().split()[0] == hashlib.sha256(binary.read_bytes()).hexdigest()
