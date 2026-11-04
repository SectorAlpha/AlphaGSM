"""Shared asset commands and setup import orchestration."""

import json
from types import SimpleNamespace

import pytest

from server import ServerError
from server.server import Server
from server import runtime
from utils.cmdparse.cmdparse import parse


def instance(tmp_path):
    server = Server.__new__(Server)
    server.name = "assets-test"
    server.data = {"dir": str(tmp_path / "server")}
    server.module = SimpleNamespace(get_asset_requirements=lambda _server: {
        "roots": ("",), "include": ("game.dat",), "required": ("game.dat",), "target": "game",
    })
    return server


def test_import_check_and_export_commands(tmp_path, monkeypatch, capsys):
    server = instance(tmp_path)
    monkeypatch.setattr(runtime, "get_runtime", lambda _s: SimpleNamespace(is_running=lambda _s: False))
    source = tmp_path / "Owned Game"
    source.mkdir()
    (source / "game.dat").write_bytes(b"owned fixture")
    server.assets("import", str(source), as_json=True)
    assert json.loads(capsys.readouterr().out)["status"] == "ready"
    server.assets("check", as_json=True)
    assert json.loads(capsys.readouterr().out)["ready"] is True
    output = tmp_path / "export.zip"
    server.assets("export", str(source), output=str(output))
    assert output.exists()


def test_live_import_is_rejected_but_checks_remain_available(tmp_path, monkeypatch):
    server = instance(tmp_path)
    monkeypatch.setattr(runtime, "get_runtime", lambda _s: SimpleNamespace(is_running=lambda _s: True))
    with pytest.raises(ServerError, match="stopped"):
        server.assets("import", str(tmp_path))
    with pytest.raises(ServerError, match="missing"):
        server.assets("check")


def test_undeclared_modules_explain_assets_are_unsupported(tmp_path):
    server = instance(tmp_path)
    server.module = SimpleNamespace()
    with pytest.raises(ServerError, match="asset"):
        server.assets("check")


def test_docker_stop_uses_module_grace_period(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime, "resolve_runtime_metadata", lambda _s: {"container_name": "halo", "stop_timeout": 30})
    monkeypatch.setattr(runtime.ContainerRuntime, "_run_check_output", lambda _self, args, **kw: calls.append(args))
    runtime.ContainerRuntime().kill(SimpleNamespace(name="halo", data={}))
    assert calls[0] == ["docker", "stop", "--time", "30", "halo"]


def test_doctor_reports_asset_readiness(tmp_path, monkeypatch):
    from server import diagnostics
    server = instance(tmp_path)
    monkeypatch.setattr(runtime, "get_runtime_doctor_report", lambda _s: {})
    report = diagnostics.get_diagnostic_report(server)
    assert next(c for c in report["checks"] if c["category"] == "assets")["status"] == "failed"
    required = tmp_path / "server/game/game.dat"
    required.parent.mkdir(parents=True)
    required.write_bytes(b"owned fixture")
    report = diagnostics.get_diagnostic_report(server)
    assert next(c for c in report["checks"] if c["category"] == "assets")["status"] == "ok"


def test_asset_options_parse_through_the_real_command_parser():
    from gamemodules import projectreclaimer
    setup = Server.default_command_args["setup"].combine(projectreclaimer.command_args["setup"])
    args, options = parse(["-n", "49176", "server dir", "--assets", "owned files.zip"], setup)
    assert args == [49176, "server dir"]
    assert options == {"ask": False, "assets_source": "owned files.zip"}
    args, options = parse(["export", "owned files", "--output", "assets.zip"], Server.default_command_args["assets"])
    assert args == ["export", "owned files"]
    assert options["output"] == "assets.zip"
