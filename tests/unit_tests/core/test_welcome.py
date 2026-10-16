"""First-run guidance is optional and cannot silently opt into remote reporting."""
from importlib import import_module
from io import StringIO
from pathlib import Path

import pytest

from utils.settings import settings


class Terminal(StringIO):
    """An isolated interactive stream without touching the real terminal."""

    def isatty(self):
        return True


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    main = import_module('core.main')
    root = tmp_path / 'operator'
    monkeypatch.setattr(settings, '_user', settings.system, raising=False)
    monkeypatch.setattr(settings._user, 'getsection',
                        lambda section: {'alphagsm_path': str(root)})
    monkeypatch.setattr(main.servermodule, 'DATAPATH', str(root / 'conf'))
    monkeypatch.setattr(main, 'help', lambda *args, **kwargs: None)
    return main, root


def replies(monkeypatch, values):
    monkeypatch.setattr('sys.stdin', Terminal())
    monkeypatch.setattr('sys.stdout', Terminal())
    values = iter(values)
    monkeypatch.setattr('builtins.input', lambda prompt: next(values))


def test_explicit_skip_records_preference_without_server_or_agent_config(isolated):
    main, root = isolated
    assert main.main('alphagsm', ['--skip-welcome']) == 0
    assert (root / 'welcome-v1.done').read_text() == 'skipped\n'
    assert not (root / 'agent').exists() and not (root / 'conf').exists()


def test_first_bare_interactive_launch_can_skip_and_does_not_repeat(isolated, monkeypatch):
    main, root = isolated
    replies(monkeypatch, [''])
    assert main.main('alphagsm', []) == 0
    assert (root / 'welcome-v1.done').is_file()
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('tour repeated'))
    assert main.main('alphagsm', []) == 2


def test_replay_remains_available_after_skip(isolated, monkeypatch):
    main, root = isolated
    root.mkdir()
    (root / 'welcome-v1.done').write_text('skipped\n')
    replies(monkeypatch, [''])
    assert main.main('alphagsm', ['--welcome']) == 0
    assert (root / 'welcome-v1.done').read_text() == 'skipped\n'


@pytest.mark.parametrize('stream', ['stdin', 'stdout'])
def test_redirected_bare_launch_never_prompts_or_writes_state(isolated, monkeypatch, stream):
    main, root = isolated
    monkeypatch.setattr('sys.stdin', Terminal())
    monkeypatch.setattr('sys.stdout', Terminal())
    monkeypatch.setattr('sys.' + stream, StringIO())
    if stream == 'stdout':
        monkeypatch.setattr(main, 'stdout', __import__('sys').stdout)
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('script prompted'))
    assert main.main('alphagsm', []) == 2
    assert not root.exists()


def test_named_commands_never_prompt_or_write_welcome_state(isolated, monkeypatch):
    main, root = isolated
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('named command prompted'))
    monkeypatch.setattr(main, 'expand_server_star', lambda user, tag, cmd: [(user, tag)])
    monkeypatch.setattr(main, 'run_one', lambda *args: 7)
    assert main.main('alphagsm', ['--version']) == 0
    assert main.main('alphagsm', ['--help']) == 0
    assert main.main('alphagsm', ['welcome', 'status']) == 7
    assert not root.exists()


def execute_tour(monkeypatch, values, execute):
    replies(monkeypatch, values)
    return import_module('core.welcome').dispatch('alphagsm', ['--welcome'], execute)


def test_tour_can_finish_without_commands_or_remote_config(isolated, monkeypatch):
    _main, root = isolated
    calls = []
    assert execute_tour(monkeypatch, ['2', ''], lambda *args: calls.append(args)) == 0
    assert calls == [] and not (root / 'agent').exists()


@pytest.mark.parametrize('approval,expected', [('', []), ('yes', [('alphagsm', ['agent', 'setup'])])])
def test_remote_wizard_needs_its_own_confirmation(isolated, monkeypatch, approval, expected):
    calls = []
    def execute(name, args):
        calls.append((name, args))
        return 0
    assert execute_tour(monkeypatch, ['3', approval, ''], execute) == 0
    assert calls == expected
    assert not any('enable-reporting' in args or 'enable-management' in args for _, args in calls)


@pytest.mark.parametrize('approval,expected', [('', []), ('y', [('alphagsm', ['world', 'create', 'teamfortress2'])])])
def test_server_record_creation_requires_preview_approval(isolated, monkeypatch, approval, expected):
    calls = []
    def execute(name, args):
        calls.append((name, args))
        return 0
    values = ['1', 'tf2', 'world', approval] + (['n'] if approval else []) + ['']
    assert execute_tour(monkeypatch, values, execute) == 0
    assert calls == expected


def test_setup_has_separate_approval_and_never_starts_the_game(isolated, monkeypatch):
    calls = []
    def execute(name, args):
        calls.append((name, args))
        return 0
    assert execute_tour(monkeypatch, ['1', 'minecraft', 'world', 'y', 'y', ''], execute) == 0
    assert calls == [('alphagsm', ['world', 'create', 'minecraft.vanilla']),
                     ('alphagsm', ['world', 'setup'])]


def test_existing_server_record_is_not_replaced(isolated, monkeypatch):
    _main, root = isolated
    (root / 'conf').mkdir(parents=True)
    path = root / 'conf/world.json'
    path.write_text('{"module":"minecraft.paper","keep":"existing world"}')
    before = path.read_bytes()
    assert execute_tour(monkeypatch, ['1', 'tf2', 'world', ''],
                        lambda *args: pytest.fail('existing server touched')) == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize('tag', ['../world', 'someuser/world', 'world;rm', '.', 'x y', 'all', 'ALL', '1', '02',
                                 'agent', 'self-update', 'start', 'create', 'version'])
def test_unsafe_names_never_reach_dispatch(isolated, monkeypatch, tag):
    assert execute_tour(monkeypatch, ['1', 'tf2', tag, ''],
                        lambda *args: pytest.fail('unsafe tag dispatched')) == 0


def test_failed_create_never_runs_setup(isolated, monkeypatch):
    calls = []
    def execute(name, args):
        calls.append((name, args))
        return 7
    assert execute_tour(monkeypatch, ['1', 'tf2', 'world', 'y'], execute) == 7
    assert calls == [('alphagsm', ['world', 'create', 'teamfortress2'])]


@pytest.mark.parametrize('exception,expected', [(EOFError, 0), (KeyboardInterrupt, 130)])
def test_cancel_does_not_run_commands_or_write_consent(isolated, monkeypatch, exception, expected):
    _main, root = isolated
    replies(monkeypatch, [])
    def cancel(prompt):
        raise exception()
    monkeypatch.setattr('builtins.input', cancel)
    assert import_module('core.welcome').dispatch('alphagsm', ['--welcome'],
        lambda *args: pytest.fail('cancel dispatched a command')) == expected
    assert not root.exists()


def test_skip_rejects_symlink_marker_without_touching_its_target(isolated):
    main, root = isolated
    root.mkdir(mode=0o700)
    target = root.parent / 'untouched'
    target.write_text('keep')
    (root / 'welcome-v1.done').symlink_to(target)
    assert main.main('alphagsm', ['--skip-welcome']) == 1
    assert target.read_text() == 'keep'


def test_skip_rejects_symlink_home(isolated):
    main, root = isolated
    target = root.parent / 'other'
    target.mkdir()
    root.symlink_to(target, target_is_directory=True)
    assert main.main('alphagsm', ['--skip-welcome']) == 1
    assert not (target / 'welcome-v1.done').exists()


def test_existing_group_writable_operator_home_needs_no_permission_change(isolated):
    main, root = isolated
    root.mkdir(mode=0o775)
    root.chmod(0o775)
    assert main.main('alphagsm', ['--skip-welcome']) == 0
    assert root.stat().st_mode & 0o777 == 0o775
    assert (root / 'welcome-v1.done').stat().st_mode & 0o777 == 0o600
