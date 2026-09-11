"""Structured diagnostics and recorded installation evidence."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import server.server as server_module
from server.settable_keys import SettingSpec
from tests.helpers import load_module_from_repo


def diagnostics():
    assert Path('src/server/diagnostics.py').exists()
    return load_module_from_repo('diagnostics_under_test', 'src/server/diagnostics.py')


def server(tmp_path):
    item = server_module.Server.__new__(server_module.Server)
    item.name = 'alpha'
    item.module = SimpleNamespace(setting_schema={'password': SettingSpec('password', secret=True)})
    item.data = {'module': 'testserver', 'dir': str(tmp_path), 'password': 'do-not-print-me'}
    return item


def test_doctor_json_is_pure_redacted_and_reports_runtime_failure(tmp_path, monkeypatch, capsys):
    item = server(tmp_path)
    def noisy_report(_server):
        print('unstructured output do-not-print-me')
        return {'configured_backend': 'docker', 'docker_cli_error': 'failed do-not-print-me',
                'command': ['server', '--token', 'other-secret', 'https://user:pass@example.org/file?sig=secret']}
    monkeypatch.setattr(server_module.runtime_module, 'get_runtime_doctor_report', noisy_report)
    with pytest.raises(server_module.ServerError):
        item.doctor(as_json=True)
    text = capsys.readouterr().out
    payload = json.loads(text)
    assert payload['schema_version'] == 1
    assert payload['status'] == 'failed'
    assert any(check['category'] == 'runtime' and check['status'] == 'failed' for check in payload['checks'])
    for secret in ('do-not-print-me', 'other-secret', 'user:pass', 'sig=secret', 'unstructured output'):
        assert secret not in text


def test_stopped_server_is_not_a_doctor_failure(tmp_path, monkeypatch, capsys):
    item = server(tmp_path)
    monkeypatch.setattr(server_module.runtime_module, 'get_runtime_doctor_report',
                        lambda _: {'resolved_runtime': 'process', 'running': False})
    item.doctor(as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert payload['status'] == 'ok'
    assert payload['runtime']['running'] is False


def test_doctor_categorizes_missing_provider_requirements_without_values(tmp_path, monkeypatch):
    item = server(tmp_path)
    item.module.get_provider_requirements = lambda _: [
        {'category': 'provider-token', 'keys': ['auth_token'], 'required_for': ['setup', 'start'], 'summary': 'Access token'}]
    module = diagnostics()
    monkeypatch.setattr(module.runtime_module, 'get_runtime_doctor_report', lambda _: {'resolved_runtime': 'process'})
    payload = module.get_diagnostic_report(item)
    assert any(check['category'] == 'provider' and check['status'] == 'failed' for check in payload['checks'])


def test_provenance_preserves_known_evidence_and_redacts_source(tmp_path, monkeypatch):
    module = diagnostics()
    item = server(tmp_path)
    artifact = tmp_path / 'release.zip'
    artifact.write_bytes(b'upstream artifact')
    item.module.get_installation_provenance = lambda _: {
        'game_version': '1.2.3', 'source_url': 'https://user:secret@example.org/release.zip?token=abc',
        'artifact_path': str(artifact), 'image_digest': 'sha256:' + 'a' * 64}
    monkeypatch.setattr(module, 'get_version', lambda: '1.0.0')
    payload = module.build_installation_provenance(item, 'setup')
    assert payload['alphagsm_version'] == '1.0.0'
    assert payload['game_version'] == '1.2.3'
    assert payload['artifact_sha256'] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert payload['image_digest'] == 'sha256:' + 'a' * 64
    assert payload['source_url'] == 'https://example.org/release.zip'
    assert 'artifact_path' not in payload


def test_provenance_leaves_unobserved_game_version_and_digest_unknown(tmp_path):
    module = diagnostics()
    item = server(tmp_path)
    item.data.update(version='latest', url='https://example.org/requested.zip')
    payload = module.build_installation_provenance(item, 'setup')
    assert payload['game_version'] is None
    assert payload['artifact_sha256'] is None
    assert payload['image_digest'] is None
    assert payload['source_url'] is None


def test_provenance_uses_atomic_write_and_failed_replacement_preserves_previous(tmp_path, monkeypatch):
    module = diagnostics()
    item = server(tmp_path)
    from server.data import JSONDataStore
    item.data = JSONDataStore(str(tmp_path / 'alpha.json'), item.data)
    item.data.save()
    path = module.record_installation_provenance(item, 'setup')
    previous = path.read_bytes()
    def fail_write(*args, **kwargs):
        raise OSError('full disk')
    monkeypatch.setattr(module, 'atomic_write_text', fail_write)
    with pytest.raises(OSError):
        module.record_installation_provenance(item, 'update')
    assert path.read_bytes() == previous


def test_setup_and_update_record_only_after_success(tmp_path, monkeypatch):
    module = diagnostics()
    item = server(tmp_path)
    item.module.commands = ('update',)
    item.module.command_args = {}
    item.module.configure = lambda *args, **kwargs: ((), {})
    item.module.install = lambda *args, **kwargs: None
    item.module.command_functions = {'update': lambda *args, **kwargs: None}
    monkeypatch.setattr(item, '_resolve_setup_port_claims', lambda *args: None)
    monkeypatch.setattr(server_module.runtime_module, 'sync_runtime_metadata', lambda *args, **kwargs: None)
    monkeypatch.setattr(server_module.runtime_module, 'assert_host_install_requirements', lambda *args, **kwargs: None)
    calls = []
    monkeypatch.setattr(server_module.diagnostics_module, 'record_installation_provenance', lambda _, action: calls.append(action))
    item.setup(ask=False)
    item.run_command('update')
    assert calls == ['setup', 'update']
    def failed(*args, **kwargs):
        raise server_module.ServerError('failed install')
    item.module.install = failed
    item.module.command_functions['update'] = failed
    with pytest.raises(server_module.ServerError):
        item.setup(ask=False)
    with pytest.raises(server_module.ServerError):
        item.run_command('update')
    assert calls == ['setup', 'update']


def test_provenance_observes_downloaded_minecraft_jar_version_and_checksum(tmp_path):
    import zipfile
    item = server(tmp_path)
    jar = tmp_path / 'server.jar'
    with zipfile.ZipFile(jar, 'w') as archive:
        archive.writestr('version.json', '{"id":"1.21.11"}')
    item.data.update(module='minecraft.vanilla', exe_name='server.jar',
                     current_url='https://example.org/server.jar', version='latest')
    payload = diagnostics().build_installation_provenance(item, 'setup')
    assert payload['game_version'] == '1.21.11'
    assert payload['artifact_sha256'] == hashlib.sha256(jar.read_bytes()).hexdigest()


def test_provenance_observes_installed_steam_build_ids(tmp_path):
    item = server(tmp_path)
    steamapps = tmp_path / 'steamapps'
    steamapps.mkdir()
    (steamapps / 'appmanifest_232250.acf').write_text('"AppState" { "appid" "232250" "buildid" "123456" }')
    payload = diagnostics().build_installation_provenance(item, 'setup')
    assert payload['steam_app_builds'] == [{'app_id': '232250', 'build_id': '123456'}]


@pytest.mark.parametrize('secret', ['a', 'failed'])
def test_short_secret_does_not_corrupt_diagnostic_status(tmp_path, monkeypatch, secret):
    item = server(tmp_path)
    item.data['password'] = secret
    module = diagnostics()
    monkeypatch.setattr(module.runtime_module, 'get_runtime_doctor_report',
                        lambda _: {'docker_cli_error': 'failed login with password ' + secret})
    payload = module.get_diagnostic_report(item)
    assert payload['status'] == 'failed'
    assert payload['checks'][0]['status'] == 'failed'
    assert payload['runtime']['docker_cli_error'].endswith('<redacted>')


def test_provenance_cannot_overwrite_a_server_named_with_installation_suffix(tmp_path):
    from server.data import JSONDataStore
    item = server(tmp_path)
    item.data = JSONDataStore(str(tmp_path / 'alpha.json'), item.data)
    existing_server = tmp_path / 'alpha.installation.json'
    existing_server.write_text('{"module":"other-server"}')
    path = diagnostics().record_installation_provenance(item, 'setup')
    assert path.parent.name == '.provenance'
    assert existing_server.read_text() == '{"module":"other-server"}'


@pytest.mark.parametrize('url', ['https://host:bad/path', 'https://[invalid/path'])
def test_malformed_urls_are_redacted_without_breaking_diagnostics(tmp_path, url):
    module = diagnostics()
    item = server(tmp_path)
    assert module._safe_url(url) is None
    assert module.redact_diagnostic(item, {'message': url}) == {'message': '<redacted-url>'}
