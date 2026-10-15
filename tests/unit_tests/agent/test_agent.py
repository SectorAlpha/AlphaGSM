"""Opt-in storage, strict origin transport and durable no-replay execution."""
from datetime import datetime, timezone
import json
import os
import pytest
from agent.config import Config, ConfigError
from agent.journal import Journal
from agent.lifecycle import Executor
from agent.transport import Transport
from test_contracts import job


def config(tmp_path):
    cfg = Config(tmp_path/'agent')
    cfg.enroll('https://control.example', dict(schema_version=1, installation_id='install-1',
        credential_generation=1, reporting=dict(key_id='report-key', secret='x'*43),
        management=dict(key_id='manage-key', secret='y'*43)))
    cfg.bind('binding-1', 'my-server', 1, actions=['status','start','stop','restart'],
        publication=False, metadata=dict(name='game',game_id='minecraft.vanilla',host='game.example',port=25565,capacity=20))
    cfg.enable(reporting=True, management=True)
    return cfg


def test_config_disabled_by_default_and_private(tmp_path):
    cfg = Config(tmp_path/'agent')
    assert cfg.load()['reporting_enabled'] is False
    assert cfg.load()['management_enabled'] is False
    cfg = config(tmp_path)
    assert os.stat(cfg.root).st_mode & 0o777 == 0o700
    assert os.stat(cfg.path).st_mode & 0o777 == 0o600
    assert 'x'*43 not in repr(cfg)
    for tag in ['*', '../other', 'user/server', '/tmp/server', 'a\\b']:
        with pytest.raises(ConfigError):
            cfg.bind('binding-2', tag, 1, actions=['start'], publication=False, metadata={})


def test_transport_rejects_untrusted_origins_and_redirects():
    for origin in ['http://control.example','https://user:pass@control.example','https://control.example/path',
                   'https://control.example?x=1','https://control.example#x']:
        with pytest.raises(ValueError):
            Transport(origin)
    from urllib.request import ProxyHandler
    assert all(not isinstance(h, ProxyHandler) or h.proxies == {} for h in Transport('https://control.example').opener.handlers)


class Runtime:
    def __init__(self):
        self.running = True
        self.calls = []
    def state(self, tag):
        return 'running' if self.running else 'stopped'
    def execute(self, tag, action):
        self.calls.append((tag, action))
        self.running = action != 'stop'


def test_duplicate_restart_and_crash_never_replay(tmp_path):
    cfg = config(tmp_path)
    runtime = Runtime()
    journal = Journal(cfg.root/'journal.json')
    calls = []
    ex = Executor(cfg, journal, runtime, lambda j: calls.append(j) or True,
                  lock=lambda tag: __import__('contextlib').nullcontext())
    j = job(); j['policy_version'] = cfg.load()['policy_version']
    first = ex.run(j)
    assert first['outcome'] == 'succeeded'
    assert ex.run(j) == first
    assert runtime.calls == [('my-server', 'restart')]
    j['job_id'] = 'crashed-job'
    journal.accept(j)
    journal.executing(j['job_id'])
    recovered = ex.run(j)
    assert recovered['outcome'] == 'unknown'
    assert len(runtime.calls) == 1
    assert len(calls) == 1


def test_final_authorization_and_local_policy_fail_closed(tmp_path):
    cfg = config(tmp_path); runtime = Runtime(); j = job(); j['policy_version'] = cfg.load()['policy_version']
    ex = Executor(cfg, Journal(cfg.root/'journal.json'), runtime, lambda job: False,
                  lock=lambda tag: __import__('contextlib').nullcontext())
    assert ex.run(j)['category'] == 'denied'
    assert runtime.calls == []
    cfg.enable(management=False)
    j['job_id'] = 'new-job'
    assert ex.run(j)['category'] == 'denied'
    assert runtime.calls == []


def test_restart_stopped_is_precondition_failure(tmp_path):
    cfg=config(tmp_path); runtime=Runtime(); runtime.running=False
    j=job(); j['policy_version']=cfg.load()['policy_version']
    ex=Executor(cfg,Journal(cfg.root/'journal.json'),runtime,lambda job:True,
                lock=lambda tag:__import__('contextlib').nullcontext())
    assert ex.run(j)['category']=='precondition'
    assert runtime.calls==[]


def test_runtime_deadline_kills_helper_and_journals_unknown(tmp_path, monkeypatch):
    import sys
    from agent.lifecycle import AlphaRuntime
    cfg = config(tmp_path)
    journal = Journal(cfg.root/'journal.json')
    runtime = AlphaRuntime()
    monkeypatch.setattr(runtime, 'state', lambda tag: 'running')
    monkeypatch.setattr(runtime, 'operation_budget', .1)
    monkeypatch.setattr(runtime, 'helper_command', lambda tag, action: [sys.executable, '-c', 'import time; time.sleep(30)'])
    ex = Executor(cfg, journal, runtime, lambda job: True,
                  lock=lambda tag: __import__('contextlib').nullcontext())
    j = job(); j['policy_version'] = cfg.load()['policy_version']
    result = ex.run(j)
    assert result['outcome'] == 'unknown'
    assert result['category'] == 'budget_exceeded'
    assert ex.run(j) == result


def test_replace_credential_preserves_policy_and_other_capability(tmp_path):
    cfg = config(tmp_path)
    old = cfg.load()
    cfg.replace_credential("reporting", "new-report", "r" * 43)
    assert cfg.load()["management"] == old["management"]
    assert cfg.load()["bindings"] == old["bindings"]
    cfg.replace_credential("management", "new-management", "m" * 43, generation=2)
    current = cfg.load()
    assert current["credential_generation"] == 2
    assert current["reporting"] == {"key_id": "new-report", "secret": "r" * 43}
    assert current["bindings"] == old["bindings"]
    with pytest.raises(ConfigError):
        cfg.replace_credential("management", "old-key", "x" * 43, generation=1)
    reporting_only = Config(tmp_path / "reporting-only")
    reporting_only.enroll("https://control.example", {
        "schema_version": 1, "installation_id": "only-report", "credential_generation": 1,
        "reporting": {"key_id": "report", "secret": "r" * 43}, "management": None})
    with pytest.raises(ConfigError):
        reporting_only.replace_credential("management", "forbidden", "m" * 43, generation=2)
