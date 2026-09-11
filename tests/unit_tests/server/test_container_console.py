"""Prove console commands reach a process through FIFO and terminal inputs."""
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest

import server.runtime as runtime_module


pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Linux container shell behavior')


def read_line(process):
    ready, _, _ = select.select([process.stdout], [], [], 3)
    assert ready, 'console fixture did not consume input'
    return process.stdout.readline().decode().rstrip('\n')


@pytest.mark.parametrize('tty', [False, True])
def test_console_fifo_consumes_input_and_preserves_attach(tmp_path, monkeypatch, tty):
    fifo = tmp_path / 'console.fifo'
    monkeypatch.setattr(runtime_module, 'CONTAINER_CONSOLE_FIFO', str(fifo), raising=False)
    spec = {'stop_mode': 'exec-console', 'stdin_open': True, 'tty': tty, 'container_name': 'fixture',
            'command': [sys.executable, '-u', '-c',
                        'import os,sys; print("READY:"+os.getcwd()+":"+os.environ["CONSOLE_FIXTURE"]); '
                        '[print("CONSUMED:"+line.rstrip("\\n")) for line in sys.stdin]']}
    assert hasattr(runtime_module, 'container_launch_command')
    command = runtime_module.container_launch_command(spec)
    master = slave = None
    if tty:
        import pty
        master, slave = pty.openpty()
    process = subprocess.Popen(command, stdin=slave if tty else subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=tmp_path,
                               env=dict(os.environ, CONSOLE_FIXTURE='kept'), start_new_session=True)
    try:
        assert read_line(process) == f'READY:{tmp_path}:kept'
        assert fifo.stat().st_mode & 0o777 == 0o600
        monkeypatch.setattr(runtime_module, 'get_container_spec', lambda _: spec)
        runtime = runtime_module.ContainerRuntime()
        def docker_exec(argv, text=False):
            assert argv[:3] == ['docker', 'exec', 'fixture']
            return subprocess.check_output(argv[3:], text=text, timeout=3)
        monkeypatch.setattr(runtime, '_run_check_output', docker_exec)
        message = 'literal "quotes" $HOME $(touch injected) `touch injected2` %s; echo nope\n'
        runtime.send_input(SimpleNamespace(), message)
        assert read_line(process) == 'CONSUMED:' + message.rstrip('\n')
        assert not (tmp_path / 'injected').exists()
        assert not (tmp_path / 'injected2').exists()
        if tty:
            os.write(master, b'from attach\n')
        else:
            process.stdin.write(b'from attach\n')
            process.stdin.flush()
        assert read_line(process) == 'CONSUMED:from attach'
    finally:
        os.killpg(process.pid, signal.SIGTERM)
        if master is not None:
            os.close(master)
            os.close(slave)
        process.communicate(timeout=3)


def test_existing_fifo_path_is_not_followed_or_overwritten(tmp_path, monkeypatch):
    target = tmp_path / 'valuable'
    target.write_text('keep')
    fifo = tmp_path / 'console.fifo'
    fifo.symlink_to(target)
    monkeypatch.setattr(runtime_module, 'CONTAINER_CONSOLE_FIFO', str(fifo), raising=False)
    assert hasattr(runtime_module, 'container_launch_command')
    command = runtime_module.container_launch_command({'stop_mode': 'exec-console', 'command': ['true']})
    result = subprocess.run(command, capture_output=True, timeout=3, check=False)
    assert result.returncode != 0
    assert target.read_text() == 'keep'


@pytest.mark.parametrize('inherited_umask', [0o022, 0o027, 0o077])
def test_console_fifo_privacy_does_not_change_game_file_permissions(
    tmp_path, monkeypatch, inherited_umask
):
    fifo = tmp_path / 'console.fifo'
    monkeypatch.setattr(runtime_module, 'CONTAINER_CONSOLE_FIFO', str(fifo))
    command = runtime_module.container_launch_command({
        'stop_mode': 'exec-console',
        'command': [sys.executable, '-c',
                    'from pathlib import Path; '
                    'Path("logs").mkdir(); Path("logs/latest.log").write_text("ready")'],
    })
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                            cwd=tmp_path, umask=inherited_umask, timeout=3, check=False)
    assert result.returncode == 0, result.stderr.decode()
    assert fifo.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / 'logs').stat().st_mode & 0o777 == 0o777 & ~inherited_umask
    assert (tmp_path / 'logs/latest.log').stat().st_mode & 0o777 == 0o666 & ~inherited_umask


@pytest.mark.parametrize('value', [None, b'stop', 'bad\0input'])
def test_console_rejects_non_text_and_nul_before_executing_docker(monkeypatch, value):
    monkeypatch.setattr(runtime_module, 'get_container_spec', lambda _: {'stop_mode': 'exec-console', 'container_name': 'fixture'})
    runtime = runtime_module.ContainerRuntime()
    monkeypatch.setattr(runtime, '_run_check_output', lambda *args, **kwargs: pytest.fail('Docker must not execute'))
    with pytest.raises(runtime_module.RuntimeError, match='text|NUL'):
        runtime.send_input(SimpleNamespace(), value)


def test_docker_stop_spec_keeps_command_and_rejects_console(monkeypatch):
    spec = {'stop_mode': 'docker-stop', 'command': ['server', '--arg']}
    assert hasattr(runtime_module, 'container_launch_command')
    assert runtime_module.container_launch_command(spec) == spec['command']
    monkeypatch.setattr(runtime_module, 'get_container_spec', lambda _: spec)
    with pytest.raises(runtime_module.RuntimeError, match='exec-console'):
        runtime_module.ContainerRuntime().send_input(SimpleNamespace(), 'stop\n')
