"""Guided onboarding uses real private policy and isolated local datastores."""
import hashlib
import json

import pytest

from agent import cli
from agent.config import Config, origin
from agent.transport import Transport, TransportError


@pytest.fixture
def local_servers(tmp_path, monkeypatch):
    import server.server as server_module
    datapath = tmp_path / 'servers'
    datapath.mkdir()
    monkeypatch.setattr(server_module, 'DATAPATH', str(datapath))

    def create(tag, **fields):
        values = {'module': 'minecraft.vanilla', 'port': 25565, 'servername': 'Local world', 'maxplayers': 20}
        values.update(fields)
        (datapath / (tag + '.json')).write_text(json.dumps(values))
        return datapath / (tag + '.json')

    create('world')
    return datapath, create


@pytest.fixture
def provider(monkeypatch):
    calls = []

    class Provider:
        def __init__(self, api_origin):
            self.origin = origin(api_origin)

        def request(self, method, path, **kwargs):
            calls.append((self.origin, method, path, kwargs))
            if path.endswith('/enroll'):
                return dict(schema_version=1, installation_id='install-1', credential_generation=1,
                            reporting=dict(key_id='report-key', secret='r' * 43),
                            management=dict(key_id='manage-key', secret='m' * 43))
            return dict(schema_version=1, binding_id='binding-' + str(len(calls)), binding_epoch=3)

    monkeypatch.setattr(cli, 'Transport', Provider)
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt: 'hidden-code')
    return calls


def answers(monkeypatch, values):
    replies = iter(values)
    monkeypatch.setattr('builtins.input', lambda prompt: next(replies))


def enrolled(tmp_path, reporting=True, management=True):
    cfg = Config(tmp_path / 'agent')
    cfg.enroll('https://control.example', dict(schema_version=1, installation_id='install-1', credential_generation=1,
        reporting=dict(key_id='report-key', secret='r' * 43) if reporting else None,
        management=dict(key_id='manage-key', secret='m' * 43) if management else None))
    return cfg


def test_root_origin_slash_is_normalized_in_storage_and_transport(tmp_path):
    assert origin('https://sector-alpha.net/') == 'https://sector-alpha.net'
    cfg = Config(tmp_path / 'agent')
    cfg.enroll('https://sector-alpha.net/', dict(schema_version=1, installation_id='i', credential_generation=1,
               reporting=None, management=None))
    assert cfg.load()['origin'] == 'https://sector-alpha.net'
    assert Transport('https://sector-alpha.net/').origin == 'https://sector-alpha.net'


def test_enroll_default_only_prompts_for_hidden_code(tmp_path, provider, monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('unexpected visible prompt'))
    assert cli.run(['enroll'], root=tmp_path / 'agent') == 0
    assert provider == [('https://sector-alpha.net', 'POST', '/v1/agent/enroll', {'payload': {'code': 'hidden-code'}})]
    assert not Config(tmp_path / 'agent').load()['management_enabled']


def test_guided_bind_infers_metadata_and_registers_only_scoped_hash(tmp_path, local_servers, provider, monkeypatch):
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'], root=cfg.root) == 0
    item = next(iter(cfg.load()['bindings'].values()))
    assert item == dict(tag='world', epoch=3, actions=[], publication=False,
                        metadata=dict(game_id='minecraft.vanilla', host='8.8.8.8', port=25565,
                                      name='Local world', capacity=20))
    assert provider == [('https://control.example', 'POST', '/v1/agent/bindings', {
        'credential': {'key_id': 'report-key', 'secret': 'r' * 43},
        'payload': {'scope': 'reporting', 'binding_ref': hashlib.sha256(b'world').hexdigest()}})]
    assert not cfg.load()['reporting_enabled']


def test_bulk_preserves_existing_binding_and_policy_on_rerun(tmp_path, local_servers, provider, monkeypatch):
    cfg = enrolled(tmp_path)
    cfg.bind('approved', 'world', 7, actions=['status'], publication=True,
             metadata=dict(game_id='minecraft.vanilla', host='approved.example', port=30000, name='Approved', capacity=30))
    old = cfg.load()
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', '*'], root=cfg.root) == 0
    assert cfg.load() == old
    assert provider == []


def test_cancel_before_registration_or_configuration(tmp_path, local_servers, provider, monkeypatch):
    cfg = Config(tmp_path / 'agent')
    answers(monkeypatch, ['', '', '', 'n'])
    assert cli.run(['bind', '*', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert provider == []
    assert not cfg.path.exists()


@pytest.mark.parametrize('scope', ['reporting', 'management'])
def test_guided_registration_uses_available_scope(tmp_path, local_servers, provider, monkeypatch, scope):
    cfg = enrolled(tmp_path, reporting=scope == 'reporting', management=scope == 'management')
    monkeypatch.setattr('builtins.input', lambda prompt: 'y' if prompt.startswith('Save these exact') else '')
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'], root=cfg.root) == 0
    assert provider[0][3]['payload']['scope'] == scope


def test_legacy_full_flags_remain_noninteractive_and_exact_game(tmp_path, local_servers, monkeypatch):
    cfg = enrolled(tmp_path)
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('legacy command prompted'))
    args = ['bind', 'legacy-id', 'world', '--game', 'minecraft.vanilla', '--host', 'game.example',
            '--port', '25565', '--name', 'World', '--actions', 'status']
    assert cli.run(args, root=cfg.root) == 0
    before = cfg.load()
    assert cli.run([value.replace('minecraft.vanilla', 'minecraft.paper') for value in args], root=cfg.root) == 1
    assert cfg.load() == before


def test_setup_enrolls_once_then_binds_all_private_without_starting(tmp_path, local_servers, provider, monkeypatch):
    local_servers[1]('tf2', module='teamfortress2', queryport='27025', port=27015, maxplayers='32')
    answers(monkeypatch, ['', '', '', '', '', '', 'y'])
    assert cli.run(['setup', '--host', '8.8.8.8'], root=tmp_path / 'agent') == 0
    value = Config(tmp_path / 'agent').load()
    assert len(value['bindings']) == 2
    assert not value['reporting_enabled'] and not value['management_enabled']
    assert {b['metadata']['port'] for b in value['bindings'].values()} == {25565, 27025}
    assert all(not b['publication'] and not b['actions'] for b in value['bindings'].values())
    assert [call[2] for call in provider] == ['/v1/agent/enroll', '/v1/agent/bindings', '/v1/agent/bindings']


def test_explicit_host_bypasses_every_discovery_and_nat_port_override(tmp_path, local_servers, provider, monkeypatch):
    from agent import onboarding
    cfg = enrolled(tmp_path)
    monkeypatch.setattr(onboarding, 'suggest_public_host', lambda metadata: pytest.fail('explicit host must bypass detection'))
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', 'public.example', '--port', '30000'], root=cfg.root) == 0
    metadata = next(iter(cfg.load()['bindings'].values()))['metadata']
    assert metadata['host'] == 'public.example' and metadata['port'] == 30000


def test_private_unprofiled_canonical_game_is_bindable(tmp_path, local_servers, provider, monkeypatch, capsys):
    local_servers[1]('terraria', module='terraria.vanilla', port=7777, servername='', maxplayers=None)
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', 'y'])
    assert cli.run(['bind', 'terraria', '--host', '8.8.8.8'], root=cfg.root) == 0
    item = next(iter(cfg.load()['bindings'].values()))
    assert item['metadata']['game_id'] == 'terraria.vanilla' and item['metadata']['name'] == 'terraria'
    assert item['metadata']['capacity'] == 0 and not item['publication']
    assert 'Public listing unavailable' in capsys.readouterr().out


def test_unsupported_publication_rejects_before_all_writes(tmp_path, local_servers, provider, monkeypatch):
    local_servers[1]('terraria', module='terraria.vanilla', port=7777)
    cfg = enrolled(tmp_path)
    old = cfg.path.read_bytes()
    answers(monkeypatch, [''])
    assert cli.run(['bind', 'terraria', '--host', '8.8.8.8', '--publish'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old and provider == []


@pytest.mark.parametrize('invalid', ['10.1.2.3:25565', 'http://public.example:25565', 'public.example:0', 'public.example:70000'])
def test_invalid_endpoint_does_not_register_or_save(tmp_path, local_servers, provider, monkeypatch, invalid):
    cfg = enrolled(tmp_path)
    old = cfg.path.read_bytes()
    answers(monkeypatch, [invalid])
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old and provider == []


@pytest.mark.parametrize('exception, expected', [(EOFError, 1), (KeyboardInterrupt, 130)])
def test_unattended_or_interrupted_guidance_never_saves(tmp_path, local_servers, provider, monkeypatch, exception, expected):
    cfg = enrolled(tmp_path)
    old = cfg.path.read_bytes()
    def reject(prompt):
        raise exception()
    monkeypatch.setattr('builtins.input', reject)
    assert cli.run(['bind', '*', '--host', '8.8.8.8'], root=cfg.root) == expected
    assert cfg.path.read_bytes() == old and provider == []


def test_bulk_reports_unconfigured_port_and_binds_other_valid_server(tmp_path, local_servers, provider, monkeypatch, capsys):
    local_servers[1]('broken', port=0, queryport='bad')
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', '*', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert [b['tag'] for b in cfg.load()['bindings'].values()] == ['world']
    assert 'Skipped broken: No valid configured port' in capsys.readouterr().out


def test_bulk_registration_partial_failure_reports_and_retains_success(tmp_path, local_servers, provider, monkeypatch, capsys):
    local_servers[1]('z-fail')
    cfg = enrolled(tmp_path)
    original = cli.Transport
    class Partial(original):
        def request(self, method, path, **kwargs):
            if kwargs['payload']['binding_ref'] == hashlib.sha256(b'z-fail').hexdigest():
                raise TransportError('offline')
            return super().request(method, path, **kwargs)
    monkeypatch.setattr(cli, 'Transport', Partial)
    answers(monkeypatch, ['', '', '', '', '', '', 'y'])
    assert cli.run(['bind', '*', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert [b['tag'] for b in cfg.load()['bindings'].values()] == ['world']
    assert 'Failed z-fail:' in capsys.readouterr().out


def test_bind_same_policy_is_idempotent_in_real_config(tmp_path):
    cfg = enrolled(tmp_path)
    metadata = dict(game_id='minecraft.vanilla', host='public.example', port=25565, name='World', capacity=20)
    cfg.bind('binding-1', 'world', 1, actions=[], publication=False, metadata=metadata)
    old = cfg.path.read_bytes()
    cfg.bind('binding-1', 'world', 1, actions=[], publication=False, metadata=metadata)
    assert cfg.path.read_bytes() == old


def test_legacy_private_binding_accepts_any_exact_canonical_game(tmp_path, local_servers, monkeypatch):
    local_servers[1]('terraria', module='terraria.vanilla', port=7777)
    cfg = enrolled(tmp_path)
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('legacy command prompted'))
    args = ['bind', 'legacy-id', 'terraria', '--game', 'terraria.vanilla', '--host', 'public.example',
            '--port', '7777', '--name', 'Terraria']
    assert cli.run(args, root=cfg.root) == 0
    old = cfg.load()
    assert cli.run(args + ['--publish'], root=cfg.root) == 1
    assert cfg.load() == old


def test_one_bulk_port_override_is_rejected_for_multiple_servers(tmp_path, local_servers, provider, monkeypatch):
    local_servers[1]('another')
    cfg = enrolled(tmp_path)
    old = cfg.path.read_bytes()
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('invalid bulk override must fail before prompts'))
    assert cli.run(['bind', '*', '--host', '8.8.8.8', '--port', '30000'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old and provider == []


@pytest.mark.parametrize('bad_origin', ['https://control.example//', 'https://control.example/?',
    'https://control.example/#', 'https://control.example/\n', 'https://control.example/?x=y'])
def test_origin_accepts_only_clean_root_trailing_slash(bad_origin):
    with pytest.raises(ValueError):
        origin(bad_origin)


@pytest.mark.parametrize('result', [
    dict(schema_version=1, binding_id='bad/id', binding_epoch=1),
    dict(schema_version=1, binding_id='good', binding_epoch=True),
    dict(schema_version=1, binding_id='good', binding_epoch=1, tag='world'),
])
def test_registration_response_is_closed_and_validated_before_save(tmp_path, local_servers, provider, monkeypatch, result):
    cfg = enrolled(tmp_path)
    old = cfg.path.read_bytes()
    class Bad:
        def __init__(self, api_origin):
            pass
        def request(self, *args, **kwargs):
            return result
    monkeypatch.setattr(cli, 'Transport', Bad)
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old


def test_registered_id_cannot_replace_another_existing_local_binding(tmp_path, local_servers, provider, monkeypatch):
    local_servers[1]('other')
    cfg = enrolled(tmp_path)
    cfg.bind('binding-1', 'other', 1, actions=['status'], publication=False,
             metadata=dict(game_id='minecraft.vanilla', host='approved.example', port=25565, name='Other', capacity=20))
    old = cfg.path.read_bytes()
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old


def test_invalid_explicit_binding_id_rejects_before_enrollment_and_prompt(tmp_path, local_servers, provider, monkeypatch):
    cfg = Config(tmp_path / 'agent')
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('invalid ID must be validated first'))
    assert cli.run(['bind', 'world', '--binding-id', 'bad/id', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert provider == [] and not cfg.path.exists()


def test_bulk_port_error_explains_single_server_override(tmp_path, local_servers, provider, capsys):
    local_servers[1]('another')
    cfg = enrolled(tmp_path)
    assert cli.run(['bind', '*', '--port', '30000', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert 'bind one tag' in capsys.readouterr().out


def test_policy_changed_during_preview_cannot_restore_permissions(tmp_path, local_servers, provider, monkeypatch):
    cfg = enrolled(tmp_path)
    metadata = dict(game_id='minecraft.vanilla', host='approved.example', port=25565, name='World', capacity=20)
    cfg.bind('approved', 'world', 3, actions=['start'], publication=False, metadata=metadata)
    prompts = iter(['', '', '', 'y'])
    def reply(prompt):
        if prompt.startswith('Save these exact'):
            cfg.bind('approved', 'world', 3, actions=[], publication=False, metadata=metadata)
        return next(prompts)
    monkeypatch.setattr('builtins.input', reply)
    assert cli.run(['bind', '*'], root=cfg.root) == 1
    assert cfg.load()['bindings']['approved']['actions'] == [] and provider == []


def test_changed_game_between_preview_and_save_is_rejected(tmp_path, local_servers, provider, monkeypatch):
    cfg = enrolled(tmp_path)
    old = cfg.path.read_bytes()
    prompts = iter(['', '', '', 'y'])
    def reply(prompt):
        if prompt.startswith('Save these exact'):
            local_servers[1]('world', module='minecraft.paper')
        return next(prompts)
    monkeypatch.setattr('builtins.input', reply)
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old and provider == []


def test_publication_guard_applies_to_existing_publication_command(tmp_path, local_servers):
    cfg = enrolled(tmp_path)
    metadata = dict(game_id='terraria.vanilla', host='public.example', port=7777, name='Terraria', capacity=20)
    cfg.bind('terraria-binding', 'terraria', 1, actions=[], publication=False, metadata=metadata)
    old = cfg.path.read_bytes()
    assert cli.run(['publication', 'terraria-binding', 'on'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old
    with pytest.raises(ValueError):
        cfg.bind('terraria-binding', 'terraria', 1, actions=[], publication=True, metadata=metadata)
    assert cfg.path.read_bytes() == old


def test_enrollment_never_falls_back_to_echoed_input(tmp_path, provider, monkeypatch):
    import getpass
    import warnings
    def no_terminal(prompt):
        warnings.warn('echoed fallback', getpass.GetPassWarning)
        return 'unsafe-code'
    monkeypatch.setattr(cli.getpass, 'getpass', no_terminal)
    assert cli.run(['enroll'], root=tmp_path / 'agent') == 1
    assert not Config(tmp_path / 'agent').path.exists() and provider == []


def test_bulk_network_fallback_is_detected_once(tmp_path, local_servers, provider, monkeypatch):
    from agent import onboarding
    cfg = enrolled(tmp_path)
    local_servers[1]('another')
    calls = []
    monkeypatch.setattr(onboarding, 'suggest_public_host', lambda metadata: calls.append(metadata) or '8.8.8.8')
    answers(monkeypatch, ['', '', '', '', '', '', 'y'])
    assert cli.run(['bind', '*'], root=cfg.root) == 0
    assert len(calls) == 1


def test_final_preview_contains_all_approved_metadata_overrides(tmp_path, local_servers, provider, monkeypatch, capsys):
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', '', 'n'])
    assert cli.run(['bind', 'world', '--host', '8.8.8.8', '--name', 'Approved title', '--capacity', '42'], root=cfg.root) == 1
    preview = next(line for line in capsys.readouterr().out.splitlines() if line.startswith('Preview:'))
    assert all(value in preview for value in ('Approved title', '42', 'minecraft.vanilla', '8.8.8.8:25565'))
    assert provider == [] and not cfg.load()['bindings']


@pytest.mark.parametrize('scope', ['reporting', 'management'])
def test_known_scope_limits_permission_prompts_and_next_steps(tmp_path, local_servers, provider, monkeypatch, capsys, scope):
    cfg = enrolled(tmp_path, reporting=scope == 'reporting', management=scope == 'management')
    prompts = []
    def reply(prompt):
        prompts.append(prompt)
        if scope == 'reporting':
            assert 'Allowed remote actions' not in prompt
        else:
            assert 'Publish this server' not in prompt
        return 'y' if prompt.startswith('Save these exact') else ''
    monkeypatch.setattr('builtins.input', reply)
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'], root=cfg.root) == 0
    output = capsys.readouterr().out
    available = 'enable-' + scope
    unavailable = 'enable-' + ('management' if scope == 'reporting' else 'reporting')
    assert available in output and unavailable not in output
    item = next(iter(cfg.load()['bindings'].values()))
    assert not item['actions'] and not item['publication']


@pytest.mark.parametrize('scope, override', [('reporting', ['--actions', 'start']), ('management', ['--publish'])])
def test_explicit_unavailable_permission_rejects_before_any_prompt(tmp_path, local_servers, provider, monkeypatch, scope, override):
    cfg = enrolled(tmp_path, reporting=scope == 'reporting', management=scope == 'management')
    old = cfg.path.read_bytes()
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('unavailable permission must reject before prompts'))
    assert cli.run(['bind', 'world', '--host', '8.8.8.8'] + override, root=cfg.root) == 1
    assert cfg.path.read_bytes() == old and provider == []


@pytest.mark.parametrize('binding_id, epoch', [('selected-id', 4), (None, None)])
def test_final_preview_shows_binding_identity_or_pending_registration(tmp_path, local_servers, provider, monkeypatch, capsys, binding_id, epoch):
    cfg = enrolled(tmp_path)
    args = ['bind', 'world', '--host', '8.8.8.8']
    if binding_id:
        args += ['--binding-id', binding_id, '--epoch', str(epoch)]
    answers(monkeypatch, ['', '', '', 'n'])
    assert cli.run(args, root=cfg.root) == 1
    preview = next(line for line in capsys.readouterr().out.splitlines() if line.startswith('Preview:'))
    if binding_id:
        assert 'binding=' + binding_id in preview and 'epoch=' + str(epoch) in preview
    else:
        assert 'binding=pending provider registration' in preview and 'epoch=pending' in preview
    assert provider == [] and not cfg.load()['bindings']


@pytest.mark.parametrize('invalid_host', ['', 'https://public.example/path', '10.1.2.3'])
def test_explicit_invalid_host_never_discovers_network_or_prompts(tmp_path, local_servers, provider, monkeypatch, invalid_host):
    from agent import onboarding
    cfg = enrolled(tmp_path)
    old = cfg.path.read_bytes()
    monkeypatch.setattr(onboarding, 'suggest_public_host', lambda metadata: pytest.fail('explicit host cannot detect network'))
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('invalid explicit host must reject before prompts'))
    assert cli.run(['bind', 'world', '--host', invalid_host], root=cfg.root) == 1
    assert cfg.path.read_bytes() == old and provider == []
