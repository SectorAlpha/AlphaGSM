"""CLI version reporting tests."""

from __future__ import annotations

from core import main as core_main


def test_main_prints_version_for_long_flag(monkeypatch, capsys):
    monkeypatch.setenv("ALPHAGSM_VERSION", "9.8.7")

    result = core_main("alphagsm", ["--version"])

    assert result == 0
    assert capsys.readouterr().out.strip() == "AlphaGSM 9.8.7"


def test_main_prints_version_for_version_command(monkeypatch, capsys):
    monkeypatch.setenv("ALPHAGSM_VERSION", "1.2.3")

    result = core_main("alphagsm", ["version"])

    assert result == 0
    assert capsys.readouterr().out.strip() == "AlphaGSM 1.2.3"