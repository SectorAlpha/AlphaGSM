"""Approved player endpoints remain separate from public query endpoints."""
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from agent import cli, preflight
from agent.contracts import ContractError, validate_metadata
from agent.inventory import read_local
from agent.lifecycle import AlphaRuntime
from agent.reporting import report_snapshot
from agent.service import Service
from test_onboarding import answers, enrolled, local_servers, provider


def metadata(**values):
    return dict(game_id='minecraft.vanilla', host='game.example', port=25565,
                name='World', capacity=20, **values)


def runtime():
    return SimpleNamespace(lock=lambda tag: nullcontext(), state=lambda tag: 'running',
                           metadata=lambda tag, approved: approved)


@pytest.mark.parametrize('connect_port', [1, 25565, 65535, None])
@pytest.mark.parametrize('game', ['minecraft.vanilla', 'teamfortress2', 'terraria.vanilla'])
def test_closed_metadata_accepts_optional_player_port_for_all_games(connect_port, game):
    item = dict(binding_id='world', binding_epoch=1, publication=False, allowed_actions=[],
                runtime_state='unknown', **metadata(connect_port=connect_port))
    item['game_id'] = game
    assert validate_metadata(item) == item
    for extra in ({'connect_port': True}, {'connect_port': 0}, {'connect_port': 65536},
                  {'connect_port': '25565'}, {'connect_port': 1.5}, {'player_port': 25565},
                  {'password': 'secret'}):
        with pytest.raises(ContractError):
            validate_metadata({**item, **extra})
    del item['connect_port']
    assert validate_metadata(item) == item


@pytest.mark.parametrize('primary,query,expected', [
    ('27015', '27025', (27015, 27025)), (25565, 'bad', (25565, 25565)),
    (False, 27025, (None, 27025)), (0, 27025, (None, 27025)),
])
def test_inventory_reads_primary_player_port_separately(local_servers, primary, query, expected):
    local_servers[1]('world', port=primary, queryport=query)
    selected = read_local('world')
    assert (selected['connect_port'], selected['port']) == expected


def test_guided_preview_approves_distinct_ports_before_registration(tmp_path, local_servers, provider, monkeypatch, capsys):
    local_servers[1]('tf2', module='teamfortress2', port=27015, queryport=27025)
    cfg = enrolled(tmp_path)
    args = ['bind', 'tf2', '--host', 'game.example', '--connect-port', '30015', '--port', '30025']
    before = cfg.path.read_bytes()
    answers(monkeypatch, ['', '', '', 'n'])
    assert cli.run(args, root=cfg.root) == 1
    preview = next(line for line in capsys.readouterr().out.splitlines() if line.startswith('Preview:'))
    assert all(value in preview for value in ('game.example', 'player port=30015', 'query port=30025'))
    assert cfg.path.read_bytes() == before and provider == []
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(args, root=cfg.root) == 0
    binding = next(iter(cfg.load()['bindings'].values()))
    assert binding['metadata']['connect_port'] == 30015 and binding['metadata']['port'] == 30025
    assert set(provider[0][3]['payload']) == {'scope', 'binding_ref'}
    assert not cfg.load()['reporting_enabled']


@pytest.mark.parametrize('game,override,expected', [
    ('minecraft.vanilla', [], 30000), ('minecraft.paper', [], 30000),
    ('minecraft.vanilla', ['--connect-port', '30001'], 30001), ('teamfortress2', [], 27015),
])
def test_query_override_tracks_minecraft_player_port_only(tmp_path, local_servers, provider, monkeypatch, game, override, expected):
    local_servers[1]('world', module=game, port=27015, queryport=27025)
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', 'game.example', '--port', '30000'] + override, root=cfg.root) == 0
    selected = next(iter(cfg.load()['bindings'].values()))['metadata']
    assert selected['port'] == 30000 and selected['connect_port'] == expected


@pytest.mark.parametrize('approved_connect,flags,expected', [
    (None, [], 25570), (25565, [], 25570), (30001, [], 30001),
    (30001, ['--port', '25569'], 25570), (None, ['--connect-port', '30001'], 30001),
])
def test_interactive_minecraft_query_edit_follows_shared_player_port(tmp_path, local_servers, provider, monkeypatch,
                                                                   approved_connect, flags, expected):
    cfg = enrolled(tmp_path)
    if approved_connect is not None:
        cfg.bind('world', 'world', 1, actions=[], publication=False,
                 metadata=metadata(connect_port=approved_connect))
    answers(monkeypatch, ['game.example:25570', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', 'game.example'] + flags, root=cfg.root) == 0
    selected = next(iter(cfg.load()['bindings'].values()))['metadata']
    assert selected['port'] == 25570 and selected['connect_port'] == expected


def test_missing_primary_port_is_reviewed_as_unknown_without_query_fallback(tmp_path, local_servers, provider, monkeypatch, capsys):
    local_servers[1]('world', port=0, queryport=25565)
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', 'game.example'], root=cfg.root) == 0
    selected = next(iter(cfg.load()['bindings'].values()))['metadata']
    assert selected['port'] == 25565 and selected['connect_port'] is None
    assert 'player port=unknown' in capsys.readouterr().out


def test_private_game_has_player_endpoint_without_new_public_profile(tmp_path, local_servers, provider, monkeypatch):
    local_servers[1]('terraria', module='terraria.vanilla', port=7777, queryport=7778)
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', 'y'])
    assert cli.run(['bind', 'terraria', '--host', 'game.example'], root=cfg.root) == 0
    selected = next(iter(cfg.load()['bindings'].values()))
    assert selected['metadata']['connect_port'] == 7777 and selected['metadata']['port'] == 7778
    assert not selected['publication']
    assert cli.run(['publication', next(iter(cfg.load()['bindings'])), 'on'], root=cfg.root) == 1


def test_old_report_omits_player_port_until_rebind_approval(tmp_path, local_servers, provider, monkeypatch, capsys):
    cfg = enrolled(tmp_path)
    cfg.bind('world', 'world', 9, actions=['status'], publication=True, metadata=metadata())
    cfg.enable(management=True)
    before = cfg.load()
    assert 'connect_port' not in report_snapshot(cfg, runtime())['bindings'][0]
    answers(monkeypatch, ['', '', '', 'n'])
    assert cli.run(['bind', 'world'], root=cfg.root) == 1
    assert 'player port=25565' in capsys.readouterr().out
    assert 'connect_port' not in cfg.load()['bindings']['world']['metadata']
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world'], root=cfg.root) == 0
    after = cfg.load()
    assert after['bindings']['world'] == {**before['bindings']['world'], 'metadata': metadata(connect_port=25565)}
    assert after['management_enabled'] and not after['reporting_enabled'] and provider == []
    snapshot = report_snapshot(cfg, runtime())['bindings'][0]
    assert snapshot['connect_port'] == 25565 and not snapshot['publication']
    stable = cfg.path.read_bytes()
    local_servers[1]('world', port=25566, queryport=25567)
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world'], root=cfg.root) == 0
    assert cfg.path.read_bytes() == stable


@pytest.mark.parametrize('port', ['0', '65536'])
def test_invalid_connection_override_does_not_prompt_or_write(tmp_path, local_servers, provider, monkeypatch, port):
    cfg = enrolled(tmp_path)
    before = cfg.path.read_bytes()
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('invalid explicit port prompted'))
    assert cli.run(['bind', 'world', '--connect-port', port], root=cfg.root) == 1
    assert cfg.path.read_bytes() == before and provider == []


def test_bulk_connection_override_does_not_apply_one_port_to_all(tmp_path, local_servers, provider, monkeypatch):
    local_servers[1]('second')
    cfg = enrolled(tmp_path)
    before = cfg.path.read_bytes()
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('ambiguous bulk override prompted'))
    assert cli.run(['bind', '*', '--connect-port', '30000'], root=cfg.root) == 1
    assert cfg.path.read_bytes() == before and provider == []


@pytest.mark.parametrize('game,flags,expected', [
    ('teamfortress2', [], 27015), ('minecraft.vanilla', [], 30025),
    ('teamfortress2', ['--connect-port', '30015'], 30015),
    ('minecraft.vanilla', ['--connect-port', '30015'], 30015),
])
def test_legacy_full_flags_infer_player_port_without_prompts(tmp_path, local_servers, monkeypatch, game, flags, expected):
    local_servers[1]('world', module=game, port=27015, queryport=27025)
    cfg = enrolled(tmp_path)
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('legacy command prompted'))
    assert cli.run(['bind', 'world-id', 'world', '--game', game, '--host', 'game.example',
                    '--port', '30025', '--name', 'World'] + flags, root=cfg.root) == 0
    selected = cfg.load()['bindings']['world-id']['metadata']
    assert selected['port'] == 30025 and selected['connect_port'] == expected


def test_runtime_refresh_cannot_infer_or_replace_approved_connection_ports(local_servers):
    local_servers[1]('world', port=27015, queryport=27025)
    assert 'connect_port' not in AlphaRuntime.metadata('world', metadata())
    selected = AlphaRuntime.metadata('world', metadata(connect_port=30015))
    assert selected['connect_port'] == 30015 and selected['port'] == 25565


def test_player_endpoint_edit_during_dns_withdraws_stale_publication(tmp_path, monkeypatch):
    cfg = enrolled(tmp_path)
    cfg.bind('world', 'world', 1, actions=[], publication=True,
             metadata=metadata(connect_port=25565), expected_public_ips=['8.8.8.8'])
    cfg.enable(reporting=True)
    def resolve(host, timeout):
        cfg.bind('world', 'world', 1, actions=[], publication=True,
                 metadata=metadata(connect_port=30000), expected_public_ips=['8.8.8.8'])
        return ['8.8.8.8']
    monkeypatch.setattr(preflight, 'resolve_host', resolve)
    sent = []
    service = Service(cfg, runtime=runtime(), transport=SimpleNamespace(
        request=lambda method, path, **kwargs: sent.append(kwargs['payload'])))
    service.report_once()
    assert sent[0]['bindings'][0]['publication'] is False
    assert cfg.load()['bindings']['world']['publication'] is True


@pytest.mark.parametrize('initial_present', [False, True])
def test_player_port_presence_change_during_dns_withdraws_then_reports_current_choice(tmp_path, monkeypatch, initial_present):
    cfg = enrolled(tmp_path)
    initial = metadata(**({'connect_port': None} if initial_present else {}))
    current = metadata(**({} if initial_present else {'connect_port': None}))
    cfg.bind('world', 'world', 1, actions=[], publication=True,
             metadata=initial, expected_public_ips=['8.8.8.8'])
    cfg.enable(reporting=True)
    resolutions = []
    def resolve(host, timeout):
        if not resolutions:
            cfg.bind('world', 'world', 1, actions=[], publication=True,
                     metadata=current, expected_public_ips=['8.8.8.8'])
        resolutions.append(host)
        return ['8.8.8.8']
    monkeypatch.setattr(preflight, 'resolve_host', resolve)
    sent = []
    service = Service(cfg, runtime=runtime(), transport=SimpleNamespace(
        request=lambda method, path, **kwargs: sent.append(kwargs['payload'])))
    service.report_once()
    assert sent[0]['bindings'][0]['publication'] is False
    assert ('connect_port' in sent[0]['bindings'][0]) is initial_present
    binding = cfg.load()['bindings']['world']
    assert binding['publication'] is True and binding['metadata'] == current
    service.report_once()
    assert sent[1]['bindings'][0]['publication'] is True
    assert ('connect_port' in sent[1]['bindings'][0]) is not initial_present
    if not initial_present:
        assert sent[1]['bindings'][0]['connect_port'] is None


@pytest.mark.parametrize('game', ['trackmaniaserver', 'enshrouded', 'arma3.headless', 'arma3headlessserver'])
def test_non_player_primary_ports_are_not_advertised_as_player_endpoints(local_servers, game):
    local_servers[1]('special', module=game, port=5000, queryport=5001)
    selected = read_local('special')
    assert selected['connect_port'] is None
    assert selected['port'] == 5001


@pytest.mark.parametrize('flags,expected', [([], None), (['--connect-port', '2350'], 2350)])
def test_trackmania_requires_explicit_player_port_approval(tmp_path, local_servers, provider, monkeypatch,
                                                         flags, expected):
    local_servers[1]('track', module='trackmaniaserver', port=5000)
    cfg = enrolled(tmp_path)
    answers(monkeypatch, ['', '', 'y'])
    assert cli.run(['bind', 'track', '--host', 'game.example'] + flags, root=cfg.root) == 0
    selected = next(iter(cfg.load()['bindings'].values()))['metadata']
    assert selected['port'] == 5000 and selected['connect_port'] == expected
