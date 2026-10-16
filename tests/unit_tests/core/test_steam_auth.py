"""Steam auth CLI dispatch, deliberately using no real Steam installation."""
import importlib
from io import StringIO

import pytest


def command_module():
    spec = importlib.util.find_spec('core.steam_auth')
    assert spec is not None, 'Steam auth CLI command is missing'
    return importlib.import_module('core.steam_auth')


def test_command_exists():
    assert command_module()


@pytest.mark.parametrize('args', [[], ['login'], ['login', 'profile'], ['login', 'p', 'u', 'password'], ['other', 'p']])
def test_bad_cli_usage_returns_two(args):
    err = StringIO()
    assert command_module().run_steam_auth('alphagsm', args, stderr=err) == 2
    assert 'Usage:' in err.getvalue()


def test_login_cli_passes_only_profile_and_username(monkeypatch):
    module = command_module()
    calls = []
    monkeypatch.setattr(module.steam_auth, 'login', lambda *args: calls.append(args))
    output = StringIO()
    assert module.run_steam_auth('alphagsm', ['login', 'owned', 'account'], stdout=output) == 0
    assert calls == [('owned', 'account')]
    assert 'local' in output.getvalue().lower()


@pytest.mark.parametrize('present', [True, False])
def test_status_cli_explicitly_limits_claim_to_local_state(monkeypatch, present):
    module = command_module()
    monkeypatch.setattr(module.steam_auth, 'status', lambda _name: {'local_session': present})
    output = StringIO()
    assert module.run_steam_auth('alphagsm', ['status', 'owned'], stdout=output) == 0
    assert 'local' in output.getvalue().lower()
    assert 'Valve' in output.getvalue()


def test_logout_cli_does_not_claim_remote_revocation(monkeypatch):
    module = command_module()
    calls = []
    monkeypatch.setattr(module.steam_auth, 'logout', lambda name: calls.append(name))
    output = StringIO()
    assert module.run_steam_auth('alphagsm', ['logout', 'owned'], stdout=output) == 0
    assert calls == ['owned']
    assert 'does not revoke' in output.getvalue()


def test_cli_handles_local_errors_without_traceback(monkeypatch):
    module = command_module()
    def fail(_profile):
        raise module.steam_auth.SteamAuthError('profile is in use')
    monkeypatch.setattr(module.steam_auth, 'status', fail)
    error = StringIO()
    assert module.run_steam_auth('alphagsm', ['status', 'owned'], stderr=error) == 1
    assert error.getvalue() == 'profile is in use\n'


def test_top_level_dispatches_before_server_lookup(monkeypatch):
    main = importlib.import_module('core.main')
    module = command_module()
    calls = []
    monkeypatch.setattr(module, 'run_steam_auth', lambda name, args, **kwargs: calls.append((name, args)) or 0)
    assert main.main('alphagsm', ['steam-auth', 'status', 'owned']) == 0
    assert calls == [('alphagsm', ['status', 'owned'])]
