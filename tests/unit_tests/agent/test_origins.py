"""Official onboarding and execution origins are selected locally, never by redirect."""
from contextlib import nullcontext
import importlib
import json
from types import SimpleNamespace

import pytest

from agent import cli
from agent.config import Config
from agent.service import Service
from agent.transport import Transport
import agent.service as service_module
from test_onboarding import answers, local_servers, provider

API = 'https://alphagsm-api.sector-alpha.net'
ALIASES = ['https://sector-alpha.net', 'https://sector-alpha.net/', 'https://sector-alpha.net:443',
           'https://SECTOR-ALPHA.NET:443/', 'HTTPS://Sector-Alpha.Net/',
           'https://ALPHAGSM-API.SECTOR-ALPHA.NET:443/']


def enrollment():
    return dict(schema_version=1, installation_id='existing-install', credential_generation=3,
                reporting=dict(key_id='old-report', secret='r' * 43),
                management=dict(key_id='old-management', secret='m' * 43))


def legacy_config(tmp_path, old):
    cfg = Config(tmp_path / 'agent')
    cfg.enroll('https://control.example', enrollment())
    cfg.bind('old-binding', 'world', 7, actions=['status', 'restart'], publication=True,
             metadata=dict(game_id='minecraft.vanilla', host='8.8.8.8', port=25565, name='World', capacity=20))
    cfg.enable(reporting=True, management=True)
    value = cfg.load()
    value['origin'] = old
    cfg.path.write_text(json.dumps(value, sort_keys=True))
    return cfg, value


@pytest.mark.parametrize('old', ALIASES)
def test_legacy_official_origin_is_normalized_locally_without_changing_relationship(tmp_path, old):
    cfg, before = legacy_config(tmp_path, old)
    original_bytes = cfg.path.read_bytes()
    loaded = cfg.load()
    assert loaded == {**before, 'origin': API}
    assert cfg.path.read_bytes() == original_bytes, 'Read-only upgrade must not write policy or credentials'
    cfg.changed()
    saved = json.loads(cfg.path.read_text())
    assert saved['origin'] == API
    assert {key: saved[key] for key in saved if key != 'dirty_at'} == {
        key: loaded[key] for key in loaded if key != 'dirty_at'}
    assert set(saved) == set(Config.defaults()) and 'reporting_origin' not in saved


@pytest.mark.parametrize('old', ALIASES)
def test_enroll_normalizes_provider_before_transport_submission(tmp_path, provider, old, monkeypatch):
    import server.server as server_module
    empty = tmp_path / 'servers'
    empty.mkdir()
    monkeypatch.setattr(server_module, 'DATAPATH', str(empty))
    assert cli.run(['enroll', '--origin', old], root=tmp_path / 'agent') == 0
    assert provider == [(API, 'POST', '/v1/agent/enroll', {'payload': {'code': 'hidden-code'}})]
    assert Config(tmp_path / 'agent').load()['origin'] == API


@pytest.mark.parametrize('custom', ['https://control.example', 'https://CONTROL.example:443',
    'https://sector-alpha.net:8443', 'https://reports.sector-alpha.net', 'https://sector-alpha.net.attacker.example',
    'https://alphagsm-api.sector-alpha.net.attacker.example', 'https://sector-alpha%2Enet',
    'https://gameserver-api.sector-alpha.net', 'https://gameserver-api.sector-alpha.net:443'])
def test_custom_and_lookalike_origins_are_not_remapped(tmp_path, custom):
    config_module = importlib.import_module('agent.config')
    canonical = getattr(config_module, 'canonical_agent_origin', None)
    assert canonical, 'missing exact trusted official-origin canonicalization'
    assert canonical(custom) == custom
    assert Transport(custom).origin == custom
    cfg = Config(tmp_path / 'agent')
    cfg.enroll(custom, enrollment())
    assert cfg.load()['origin'] == custom


@pytest.mark.parametrize('unsafe', ['http://sector-alpha.net', 'https://sector-alpha.net/agent',
    'https://sector-alpha.net?next=attacker', 'https://sector-alpha.net#attacker',
    'https://user@sector-alpha.net', 'https://sector-alpha.net@attacker.example'])
def test_alias_mapping_never_relaxes_origin_validation(unsafe):
    config_module = importlib.import_module('agent.config')
    canonical = getattr(config_module, 'canonical_agent_origin', None)
    assert canonical, 'missing exact trusted official-origin canonicalization'
    with pytest.raises(ValueError):
        canonical(unsafe)


def test_old_relationship_uses_one_new_api_transport_for_reporting_and_management(tmp_path, monkeypatch):
    cfg, before = legacy_config(tmp_path, 'https://SECTOR-ALPHA.NET:443/')
    constructed, sent = [], []
    class Provider:
        def __init__(self, api_origin):
            constructed.append(api_origin)
        def request(self, method, path, **kwargs):
            sent.append((method, path, kwargs))
            return {'job': None}
    monkeypatch.setattr(service_module, 'Transport', Provider)
    runtime = SimpleNamespace(lock=lambda tag: nullcontext(), state=lambda tag: 'running', metadata=lambda tag, approved: approved)
    service = Service(cfg, runtime=runtime)
    service.report_once()
    service.management_once()
    assert constructed == [API] and service.relationship == (API, before['installation_id'])
    assert [path for method, path, kwargs in sent] == ['/v1/agent/reports', '/v1/agent/policy', '/v1/agent/jobs']
    assert sent[0][2]['credential'] == before['reporting']
    assert all(kwargs['credential'] == before['management'] for method, path, kwargs in sent[1:])
    assert cfg.load()['bindings'] == before['bindings'] and cfg.load()['policy_version'] == before['policy_version']


def test_legacy_registration_preserves_provider_and_existing_bindings(tmp_path, local_servers, provider, monkeypatch):
    local_servers[1]('new-server')
    cfg, before = legacy_config(tmp_path, 'https://sector-alpha.net')
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'new-server', '--host', '8.8.8.8', '--origin', 'https://SECTOR-ALPHA.NET:443/'], root=cfg.root) == 0
    assert provider[0][0:3] == (API, 'POST', '/v1/agent/bindings')
    assert provider[0][3]['credential'] == before['reporting']
    assert cfg.load()['bindings']['old-binding'] == before['bindings']['old-binding']


def test_direct_transport_canonicalizes_old_official_origin_before_credentials():
    assert Transport('https://SECTOR-ALPHA.NET:443/').origin == API


@pytest.mark.parametrize('provider,destination', [
    *[(alias, API) for alias in [API, API + ':443/', *ALIASES]],
    ('https://control.example', 'https://control.example'),
    ('https://sector-alpha.net:8443', 'https://sector-alpha.net:8443'),
    ('https://alphagsm-api.sector-alpha.net.attacker.example',
     'https://alphagsm-api.sector-alpha.net.attacker.example'),
])
def test_transport_uses_the_configured_origin_for_every_operation(monkeypatch, provider, destination):
    transport = Transport(provider)
    sent = []
    def capture(request, _timeout):
        sent.append((request.full_url, request.get_method(), request.get_header('Authorization')))
        return {'accepted': True}
    monkeypatch.setattr(transport, '_read_response', capture)
    credential = {'key_id': 'test-key', 'secret': 's' * 43}
    for method, path in (
        ('POST', '/v1/agent/enroll'),
        ('POST', '/v1/agent/bindings'),
        ('POST', '/v1/agent/challenge'),
        ('POST', '/v1/agent/reports'),
        ('POST', '/v1/agent/policy'),
        ('GET', '/v1/agent/jobs'),
        ('POST', '/v1/agent/jobs/job-1/authorize'),
        ('POST', '/v1/agent/results'),
    ):
        transport.request(method, path, credential=credential)
        assert sent[-1] == (destination + path, method, 'Bearer test-key.' + 's' * 43)
    assert transport.origin == destination
