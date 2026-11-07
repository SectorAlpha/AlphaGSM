"""Runtime log consumers can read output without exposing it to the terminal."""

from types import SimpleNamespace

import pytest

import server.runtime as runtime_module


@pytest.mark.parametrize("lines,expected", [(None, "first\nlast\n"), (1, "last\n"), (0, "")])
def test_process_read_logs(tmp_path, monkeypatch, capsys, lines, expected):
    path = tmp_path / "console.log"
    path.write_text("first\nlast\n")
    monkeypatch.setattr(runtime_module.screen, "logpath", lambda _name: str(path))
    assert runtime_module.ProcessRuntime().read_logs(SimpleNamespace(name="voice"), lines) == expected
    assert capsys.readouterr() == ("", "")


def test_docker_read_logs_captures_both_streams(monkeypatch, capsys):
    monkeypatch.setattr(runtime_module, "get_container_spec", lambda _server: {"container_name": "voice"})

    def run(command, **kwargs):
        assert command == ["docker", "logs", "--tail", "all", "voice"]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        return SimpleNamespace(returncode=0, stdout="stdout\n", stderr="stderr\n")

    monkeypatch.setattr(runtime_module.sp, "run", run)
    assert runtime_module.ContainerRuntime().read_logs(SimpleNamespace(), None) == "stdout\nstderr\n"
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("backend", [runtime_module.ProcessRuntime, runtime_module.ContainerRuntime])
@pytest.mark.parametrize("lines", [-1, "all", 1.5])
def test_read_logs_rejects_invalid_counts(backend, lines):
    with pytest.raises(runtime_module.RuntimeError, match="nonnegative integer"):
        backend().read_logs(SimpleNamespace(), lines)


def test_failed_docker_logs_do_not_expose_captured_output(monkeypatch, capsys):
    monkeypatch.setattr(runtime_module, "get_container_spec", lambda _server: {"container_name": "voice"})
    monkeypatch.setattr(runtime_module.sp, "run", lambda *_args, **_kwargs:
                        SimpleNamespace(returncode=1, stdout="private", stderr="sensitive"))
    with pytest.raises(runtime_module.RuntimeError, match="^Failed to read docker logs for: voice$"):
        runtime_module.ContainerRuntime().read_logs(SimpleNamespace(), None)
    assert capsys.readouterr() == ("", "")
