"""Explicit agent routes cannot be interpreted as server selectors."""
import json
from agent.cli import run
from agent.config import Config


def test_disable_does_not_require_a_provider(tmp_path, capsys):
    assert run(['disable-reporting'], root=tmp_path/'agent') == 0
    assert not Config(tmp_path/'agent').load()['reporting_enabled']
    assert run(['status'], root=tmp_path/'agent') == 0
    assert 'secret' not in capsys.readouterr().out


def test_secret_command_line_options_are_rejected(tmp_path):
    assert run(['enroll', '--secret', 'unsafe-argument'], root=tmp_path/'agent') == 2
