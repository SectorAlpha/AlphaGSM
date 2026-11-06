"""Strict shared wire schema: no strings converted into permissions."""
from datetime import datetime, timedelta, timezone
import pytest
from agent.contracts import validate_job, validate_report, validate_result, ContractError


def job():
    now = datetime.now(timezone.utc)
    return dict(schema_version=1, job_id='job-1', installation_id='install-1',
                binding_id='binding-1', binding_epoch=1, action='restart', policy_version=1,
                credential_generation=1, requested_by='owner-1',
                issued_at=now.isoformat(), expires_at=(now + timedelta(seconds=120)).isoformat())


def test_job_accepts_only_closed_action_contract():
    assert validate_job(job())['action'] == 'restart'
    for update in ({'action': 'kill'}, {'arguments': []}, {'policy_version': True},
                   {'binding_id': '../other'}, {'action': ['start']}, {'expires_at': 'tomorrow'}):
        with pytest.raises(ContractError):
            validate_job({**job(), **update})


def test_report_rejects_private_fields_and_false_string_consent():
    report = dict(schema_version=1, installation_id='install-1', sequence=1, policy_version=1,
                  bindings=[dict(binding_id='binding-1', binding_epoch=1, publication=False,
                                 name='My server', game_id='minecraft.vanilla', host='game.example',
                                 port=25565, capacity=20, runtime_state='stopped', allowed_actions=['status'])])
    assert validate_report(report)['bindings'][0]['publication'] is False
    for extra in ({'password': 'secret'}, {'publication': 'false'}, {'capacity': -1}, {'allowed_actions': ['shell']}):
        with pytest.raises(ContractError):
            validate_report({**report, 'bindings': [{**report['bindings'][0], **extra}]})


def test_result_never_accepts_raw_console_or_unknown_state():
    result = dict(schema_version=1, job_id='job-1', installation_id='install-1',
                  outcome='succeeded', runtime_state='running', category='ok',
                  observed_at=datetime.now(timezone.utc).isoformat())
    assert validate_result(result) == result
    with pytest.raises(ContractError):
        validate_result({**result, 'logs': 'console output'})
