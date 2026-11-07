"""TeamSpeak queries use private credentials from the active runtime."""

from types import SimpleNamespace
import stat

import pytest

from gamemodules import ts3server


@pytest.mark.parametrize("backend", ["process", "docker"])
def test_credentials_from_runtime_survive_log_rotation(tmp_path, monkeypatch, capsys, backend):
    server = SimpleNamespace(name="voice", data={"dir": str(tmp_path), "runtime": backend})
    calls = []

    def logs(actual_server, lines):
        assert actual_server is server
        assert lines is None
        calls.append("logs")
        return 'loginname= "serveradmin", password= "fixture-secret"\n'

    monkeypatch.setattr(ts3server.runtime_module, "read_server_logs", logs, raising=False)
    assert ts3server.get_query_credentials(server) == ("serveradmin", "fixture-secret")
    cached = tmp_path / "serverquery_admin_password.txt"
    assert cached.read_text().strip() == "fixture-secret"
    assert stat.S_IMODE(cached.stat().st_mode) == 0o600
    assert ts3server.get_query_credentials(server) == ("serveradmin", "fixture-secret")
    assert calls == ["logs"]
    assert capsys.readouterr() == ("", "")


def test_missing_runtime_logs_do_not_leak_errors(tmp_path, monkeypatch, capsys):
    server = SimpleNamespace(name="voice", data={"dir": str(tmp_path)})

    def missing(*_args, **_kwargs):
        raise ts3server.runtime_module.RuntimeError("private log unavailable")

    monkeypatch.setattr(ts3server.runtime_module, "read_server_logs", missing, raising=False)
    assert ts3server.get_query_credentials(server) is None
    assert capsys.readouterr() == ("", "")
