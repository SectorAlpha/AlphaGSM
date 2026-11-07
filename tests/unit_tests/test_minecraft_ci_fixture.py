"""The pinned CI fixture must survive runner user changes and avoid latest drift."""
from pathlib import Path

import pytest

from tests.smoke_tests import minecraft_status


def test_pinned_minecraft_fixture_does_not_resolve_latest(monkeypatch, capsys):
    monkeypatch.setenv("ALPHAGSM_MINECRAFT_RELEASE_ID", "1.21.11")
    monkeypatch.setenv("ALPHAGSM_MINECRAFT_SERVER_URL", "https://example.com/server.jar")
    monkeypatch.setattr(minecraft_status.urllib.request, "urlopen",
                        lambda *_args, **_kwargs: pytest.fail("Pinned fixture must not query upstream"))
    assert minecraft_status._latest_release() == 0
    assert capsys.readouterr().out == "1.21.11\thttps://example.com/server.jar\n"


def test_incomplete_fixture_pin_fails_instead_of_selecting_latest(monkeypatch, capsys):
    monkeypatch.setenv("ALPHAGSM_MINECRAFT_RELEASE_ID", "1.21.11")
    monkeypatch.delenv("ALPHAGSM_MINECRAFT_SERVER_URL", raising=False)
    assert minecraft_status._latest_release() == 1
    assert "both" in capsys.readouterr().err


def test_ci_user_switches_preserve_minecraft_fixture_inputs():
    workflow = Path(".github/workflows/unittest.yaml").read_text(encoding="utf-8")
    switches = [line for line in workflow.splitlines() if "su " in line and "gsmuser -c" in line]
    assert len(switches) == 3
    for line in switches:
        assert "--whitelist-environment=" in line
        assert "ALPHAGSM_MINECRAFT_RELEASE_ID" in line
        assert "ALPHAGSM_MINECRAFT_SERVER_URL" in line
