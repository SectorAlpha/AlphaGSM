"""Frozen bulk commands must re-execute the binary without sibling scripts."""
from importlib import import_module


def test_frozen_internal_command_uses_current_executable(monkeypatch):
    module = import_module("core.main")
    import sys
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/isolated bin/alphagsm")
    assert module.get_run_cmd("alphagsm", "demo", ["status"], multi=True) == [
        "/isolated bin/alphagsm", "--_run-command", "1", "alphagsm", "demo", "status",
    ]


@__import__('pytest').mark.parametrize('marker', ['0', '1'])
def test_hidden_worker_dispatch_runs_without_a_sibling_script(monkeypatch, capsys, marker):
    from pathlib import Path
    import runpy
    import sys
    from types import SimpleNamespace
    import pytest

    launcher = Path(__file__).resolve().parents[3] / 'alphagsm'
    calls = []
    def main(name, args):
        calls.append((name, args))
        return 7
    monkeypatch.setitem(sys.modules, 'core', SimpleNamespace(main=main))
    monkeypatch.setattr(sys, 'path', list(sys.path))
    monkeypatch.setattr(sys, 'argv', ['C:/standalone/AlphaGSM.exe', '--_run-command', marker,
                                    'AlphaGSM display name', 'server with spaces', 'send', 'literal & text'])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(launcher), run_name='__main__')
    assert result.value.code == 7
    assert calls == [('AlphaGSM display name', ['server with spaces', 'send', 'literal & text'])]
    assert capsys.readouterr().out == ('#%AlphaGSM-INTERNAL%#\n' if marker == '1' else '')


@__import__('pytest').mark.parametrize('codes, expected', [((0, 0), 0), ((0, 3), 3), ((2, 3), 10)])
def test_windows_bulk_commands_preserve_frozen_argv_and_failure_codes(monkeypatch, capsys, codes, expected):
    import sys
    from types import SimpleNamespace

    module = import_module('core.main')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', 'C:/isolated bin/AlphaGSM.exe')
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        assert kwargs['stdin'] == module.sp.DEVNULL
        assert kwargs['stdout'] == module.sp.PIPE
        assert kwargs['stderr'] == module.sp.STDOUT
        assert kwargs.get('shell', False) is False
        return SimpleNamespace(returncode=codes[0 if command[4] == 'alpha' else 1], stdout='result\n')
    monkeypatch.setattr(module.sp, 'run', run)
    assert module._run_multi_windows('AlphaGSM', [(None, 'alpha'), (None, 'beta')], ['status']) == expected
    assert sorted(commands) == [
        ['C:/isolated bin/AlphaGSM.exe', '--_run-command', '0', 'AlphaGSM', name, 'status']
        for name in ('alpha', 'beta')]
    assert 'alpha: result' in capsys.readouterr().out


def test_windows_bulk_launch_failure_is_reported_without_masking_other_targets(monkeypatch, capsys):
    module = import_module('core.main')
    monkeypatch.setattr(module, 'get_run_cmd', lambda name, tag, args: [tag])
    from types import SimpleNamespace
    def run(command, **kwargs):
        if command == ['alpha']:
            raise OSError('worker could not launch')
        return SimpleNamespace(returncode=0, stdout='other target ran')
    monkeypatch.setattr(module.sp, 'run', run)
    assert module._run_multi_windows('AlphaGSM', [(None, 'alpha'), (None, 'beta')], ['status']) == 1
    output = capsys.readouterr().out
    assert 'alpha: worker could not launch' in output
    assert 'beta: other target ran' in output
