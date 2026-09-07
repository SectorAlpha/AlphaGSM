"""Reject incompatible native executables without launching them."""
from types import SimpleNamespace

import pytest

from server import platform_support


def server(**attributes):
    return SimpleNamespace(name='example', data={'module': 'example'}, module=SimpleNamespace(**attributes))


@pytest.mark.parametrize('magic, host', [(b'\x7fELF', 'windows'), (b'\x7fELF', 'macos'),
                                       (b'MZ', 'linux'), (b'\xcf\xfa\xed\xfe', 'windows'),
                                       (b'#!/bin/sh\n', 'windows')])
def test_incompatible_binary_format_rejected_even_without_metadata(tmp_path, magic, host):
    executable = tmp_path / 'server'
    executable.write_bytes(magic + b'\0' * 64)
    with pytest.raises(platform_support.PlatformCompatibilityError, match='Docker|Wine|interpreter'):
        platform_support.validate_process_command(server(), [str(executable)], str(tmp_path), host=host)


@pytest.mark.parametrize('magic, host', [(b'\x7fELF', 'linux'), (b'MZ', 'windows'),
                                       (b'\xcf\xfa\xed\xfe', 'macos')])
def test_matching_executable_format_allowed(tmp_path, magic, host):
    executable = tmp_path / 'server'
    executable.write_bytes(magic + b'\0' * 64)
    platform_support.validate_process_command(server(), ['./server'], str(tmp_path), host=host)


def test_declared_process_platform_rejected_before_setup():
    with pytest.raises(platform_support.PlatformCompatibilityError, match='linux.*windows'):
        platform_support.validate_declared_platform(server(process_platforms=['linux']), host='windows')


def test_unknown_platform_does_not_claim_verified_support():
    result = platform_support.platform_declaration(server(), host='windows')
    assert result['host'] == 'windows'
    assert result['supported'] is None
    assert result['declared_platforms'] is None
    assert result['declared_architectures'] is None


def test_wine_wrapper_can_run_windows_payload_on_linux(tmp_path):
    wine = tmp_path / 'wine64'
    wine.write_bytes(b'\x7fELF' + b'\0' * 64)
    payload = tmp_path / 'server.exe'
    payload.write_bytes(b'MZ' + b'\0' * 64)
    platform_support.validate_process_command(server(supported_platforms=['windows']),
                                             [str(wine), str(payload)], str(tmp_path), host='linux')


def test_missing_executable_remains_a_normal_launch_error(tmp_path):
    platform_support.validate_process_command(server(), ['./absent'], str(tmp_path), host='windows')


def test_explicit_python_interpreter_does_not_reject_script_argument(tmp_path):
    python = tmp_path / 'python.exe'
    python.write_bytes(b'MZ' + b'\0' * 64)
    script = tmp_path / 'server.py'
    script.write_text('#!/usr/bin/python3\n')
    platform_support.validate_process_command(server(), [str(python), str(script)], str(tmp_path), host='windows')


def test_game_requirements_vary_with_selected_build():
    example = server(get_platform_requirements=lambda value: {'process': {
        'platforms': ['windows' if value.data.get('build') == 'windows' else 'linux'],
        'architectures': ['x86_64']}})
    with pytest.raises(platform_support.PlatformCompatibilityError):
        platform_support.validate_declared_platform(example, host='windows', architecture='amd64')
    example.data['build'] = 'windows'
    platform_support.validate_declared_platform(example, host='windows', architecture='amd64')
    with pytest.raises(platform_support.PlatformCompatibilityError, match='x86_64'):
        platform_support.validate_declared_platform(example, host='windows', architecture='arm64')


def test_process_runtime_checks_payload_before_launch(tmp_path, monkeypatch):
    from server import runtime
    executable = tmp_path / 'linux-server'
    executable.write_bytes(b'\x7fELF' + b'\0' * 64)
    example = server(get_start_command=lambda *_: ([str(executable)], str(tmp_path)))
    monkeypatch.setattr(platform_support, 'PLATFORM', 'windows')
    monkeypatch.setattr(runtime, 'assert_host_install_requirements', lambda *a, **k: None)
    monkeypatch.setattr(runtime.screen, 'start_screen', lambda *a, **k: pytest.fail('must reject before launch'))
    with pytest.raises(runtime.RuntimeError, match='ELF'):
        runtime.ProcessRuntime().start(example)


def test_server_rejects_declared_platform_before_install_and_prestart(monkeypatch):
    from tests.unit_tests.server.test_server import make_server
    from server import runtime
    from server import ServerError
    example = make_server()
    example.module.process_platforms = ['linux']
    example.module.install = lambda *a, **k: pytest.fail('must reject before download')
    example.module.prestart = lambda *a, **k: pytest.fail('must reject before prestart')
    monkeypatch.setattr(platform_support, 'PLATFORM', 'windows')
    monkeypatch.setattr(runtime.screen, 'check_screen_exists', lambda _: False)
    with pytest.raises(ServerError, match='linux.*windows'):
        example.setup(ask=False)
    with pytest.raises(ServerError, match='linux.*windows'):
        example.start()


def test_existing_native_architecture_declaration_is_enforced():
    with pytest.raises(platform_support.PlatformCompatibilityError, match='x86_64'):
        platform_support.validate_declared_platform(server(supported_architectures=['x86_64']),
                                                    host='linux', architecture='arm64')


def test_relative_path_search_uses_child_working_directory(tmp_path, monkeypatch):
    import os
    if os.name == 'nt':
        pytest.skip('POSIX exec uses child cwd for relative PATH entries')
    executable = tmp_path / 'server'
    executable.write_bytes(b'MZ' + b'\0' * 64)
    executable.chmod(0o755)
    monkeypatch.setenv('PATH', '.')
    with pytest.raises(platform_support.PlatformCompatibilityError, match='PE/Windows'):
        platform_support.validate_process_command(server(), ['server'], str(tmp_path), host='linux')


def test_tf2_process_declaration_matches_its_linux_launcher():
    from importlib import import_module
    module = import_module('gamemodules.teamfortress2')
    example = SimpleNamespace(module=module, data={'module': 'teamfortress2'}, name='tf2')
    with pytest.raises(platform_support.PlatformCompatibilityError, match='linux.*windows'):
        platform_support.validate_declared_platform(example, host='windows')


@pytest.mark.parametrize('value', [[], 1, 'macos', ''])
def test_invalid_container_os_declaration_fails_clearly(value):
    example = server(get_platform_requirements=lambda _: {'docker': {'operating_system': value}})
    with pytest.raises(platform_support.PlatformCompatibilityError, match='operating_system'):
        platform_support.normalized_platform_requirements(example)


def test_update_checks_selected_game_build_before_downloading(monkeypatch):
    from tests.unit_tests.server.test_server import make_server
    from server import ServerError
    example = make_server()
    example.module.commands = ['update']
    example.module.process_platforms = ['linux']
    example.module.command_functions = {'update': lambda *a: pytest.fail('must reject before download')}
    monkeypatch.setattr(platform_support, 'PLATFORM', 'windows')
    with pytest.raises(ServerError, match='linux.*windows'):
        example.run_command('update')


def test_human_doctor_displays_platform_rejection(capsys):
    from server import runtime
    runtime.print_runtime_doctor_report(server(), report={
        'resolved_runtime': 'process', 'running': False,
        'platform_error': 'This game build requires Linux; this host is Windows.'})
    assert 'This game build requires Linux; this host is Windows.' in capsys.readouterr().out
