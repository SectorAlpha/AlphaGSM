"""Native Wreckfest registry capture must use a fresh selected-prefix probe."""

from types import SimpleNamespace
import subprocess

import pytest

import utils.proton as proton
from tests.smoke_tests import wreckfestserver_workshop as module


@pytest.mark.parametrize("container", [None, "alphagsm-owned-wreckfest"])
def test_native_probe_selects_private_runtime_and_parses_only_its_new_file(tmp_path, monkeypatch, container):
    install = tmp_path / 'server'
    install.mkdir()
    (install / 'Wreckfest_x64.exe').write_bytes(b'fixture executable')
    helper = tmp_path / 'console-probe.exe'
    helper.write_bytes(b'fixture helper')
    calls = []
    monkeypatch.setattr(proton, 'wrap_command', lambda command, **options: calls.append(options) or ['wine', *command])
    native = 'Tracks:\n  crazy_2000_classic (CRAZY 2000)\n'

    def run(command, **options):
        calls.append((command, options))
        evidence = next((install / '.alphagsm/native-probes').glob('*.log'), None)
        assert evidence is None, 'Evidence must not exist before the native capture'
        windows_path = command[-1]
        relative = windows_path.replace('\\', '/').split('/.alphagsm/', 1)[1]
        (install / '.alphagsm' / relative).write_text(native)
        return SimpleNamespace(returncode=0, stdout='', stderr='')

    result = module.capture_native_registry(install, container=container, helper_path=str(helper), runner=run)
    assert result == native
    command, options = calls[-1]
    assert options['timeout'] == 45 and options['check']
    assert command[-2].endswith('Wreckfest_x64.exe')
    if container:
        assert command[:2] == ['docker', 'exec']
        assert 'WINEPREFIX=/srv/server/.alphagsm-wineprefix' in command
        assert container in command
    else:
        assert calls[0] == {'wineprefix': str(install / '.alphagsm-wineprefix'), 'prefer_proton': True}


def test_probe_command_failure_cannot_reuse_old_registry(tmp_path):
    install = tmp_path / 'server'
    install.mkdir()
    (install / 'Wreckfest_x64.exe').write_bytes(b'fixture')
    old = install / '.alphagsm/native-probes/old.log'
    old.parent.mkdir(parents=True)
    old.write_text('Tracks:\n  crazy_2000_classic (OLD)\n')
    def fail(command, **_options):
        raise subprocess.CalledProcessError(1, command, stderr='native attach failed')
    with pytest.raises(subprocess.CalledProcessError):
        module.capture_native_registry(install, container='owned', runner=fail)
    assert old.read_text().endswith('(OLD)\n')


def test_probe_requires_a_single_installed_executable(tmp_path):
    with pytest.raises(AssertionError, match='executable'):
        module.capture_native_registry(tmp_path, container='owned')
