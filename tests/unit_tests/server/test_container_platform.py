"""Docker platform eligibility depends on the daemon, not the CLI host OS."""

from types import SimpleNamespace

import pytest

import server.runtime as runtime_module


INFO_COMMAND = ["docker", "info", "--format", "{{.OSType}}"]


def _spec(family="java", **extra):
    return {"runtime_family": family, "image": "example/runtime:1", "container_name": "alphagsm-platform",
            "stop_mode": "docker-stop", "stdin_open": False, "command": ["server"],
            "env": {}, "mounts": [], "ports": [], **extra}


@pytest.mark.parametrize("family", ["java", "quake-linux", "service-console", "simple-tcp", "steamcmd-linux", "wine-proton"])
def test_linux_family_rejects_windows_daemon_before_image_work(monkeypatch, family):
    runtime = runtime_module.ContainerRuntime()
    calls = []
    monkeypatch.setattr(runtime_module, "_get_module_runtime_requirements", lambda _server: {})
    monkeypatch.setattr(runtime_module, "get_container_spec", lambda *_args, **_kwargs: _spec(family))

    def docker(command, text=False):
        calls.append(command)
        if command == INFO_COMMAND:
            return "windows\n"
        return "false\n" if "inspect" in command else "created\n"

    monkeypatch.setattr(runtime, "_run_check_output", docker)
    with pytest.raises(runtime_module.RuntimeError, match="requires Linux containers"):
        runtime.start(SimpleNamespace(name="platform"))
    assert calls == [INFO_COMMAND]


def test_windows_host_accepts_linux_container_daemon(monkeypatch):
    import sys

    runtime = runtime_module.ContainerRuntime()
    calls = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(runtime_module, "_get_module_runtime_requirements", lambda _server: {})
    monkeypatch.setattr(runtime_module, "get_container_spec", lambda *_args, **_kwargs: _spec())

    def docker(command, text=False):
        calls.append(command)
        if command == INFO_COMMAND:
            return "linux\n"
        if command[:2] == ["docker", "inspect"]:
            raise runtime_module.RuntimeError("container does not exist")
        return "ok\n"

    monkeypatch.setattr(runtime, "_run_check_output", docker)
    runtime.start(SimpleNamespace(name="platform"))
    assert calls[0] == INFO_COMMAND
    assert calls[-1][:3] == ["docker", "run", "-d"]


@pytest.mark.parametrize("declared, daemon, expected", [(None, "windows", None), ("windows", "windows", True), ("linux", "windows", False)])
def test_custom_spec_reports_explicit_or_unknown_container_os(monkeypatch, declared, daemon, expected):
    runtime = runtime_module.ContainerRuntime()
    monkeypatch.setattr(runtime, "_run_check_output", lambda *_args, **_kwargs: daemon)
    spec = _spec("custom-family")
    if declared:
        spec["container_os"] = declared
    report = runtime.container_platform_report(spec)
    assert report["container_os"] == (declared or "unknown")
    assert report["docker_daemon_os"] == daemon
    assert report["container_os_compatible"] is expected


def test_doctor_reports_daemon_mismatch_without_inspecting_images(monkeypatch):
    from tests.unit_tests.server.test_runtime import DummyServer, _set_runtime_backend

    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(data={"runtime": "docker"}, module=SimpleNamespace(
        get_runtime_requirements=lambda _server: {"runtime": "docker", "runtime_family": "java"},
        get_container_spec=lambda _server: _spec(),
    ))
    calls = []

    def docker(command, text=False):
        calls.append(command)
        if command == INFO_COMMAND:
            return "windows\n"
        if command[:2] == ["docker", "version"]:
            return "27.0.0\n"
        return "false\n"

    monkeypatch.setattr(runtime_module.ContainerRuntime, "_run_check_output", staticmethod(docker))
    report = runtime_module.get_runtime_doctor_report(server)
    assert report["docker_daemon_os"] == "windows"
    assert report["container_os"] == "linux"
    assert report["container_os_compatible"] is False
    assert "Switch Docker Desktop to Linux containers" in report["container_platform_error"]
    assert all(command[:2] not in (["docker", "image"], ["docker", "inspect"]) for command in calls)


def test_game_build_declaration_overrides_generic_spec(monkeypatch):
    runtime = runtime_module.ContainerRuntime()
    server = SimpleNamespace(name="platform", module=SimpleNamespace(
        get_platform_requirements=lambda _server: {"docker": {"operating_system": "windows"}},
    ))
    monkeypatch.setattr(runtime, "_run_check_output", lambda *_args, **_kwargs: "linux")
    with pytest.raises(runtime_module.RuntimeError, match="requires Windows containers"):
        runtime.assert_platform_compatible(server, _spec("custom-family"))


def test_pre_setup_platform_check_does_not_need_install_dependent_spec(monkeypatch):
    runtime = runtime_module.ContainerRuntime()
    server = SimpleNamespace(name="platform", module=SimpleNamespace(
        get_platform_requirements=lambda _server: {"docker": {"operating_system": "linux"}},
    ))
    monkeypatch.setattr(runtime_module, "resolve_runtime_metadata", lambda _server: {"runtime": "docker"})
    monkeypatch.setattr(runtime, "_run_check_output", lambda *_args, **_kwargs: "windows")
    with pytest.raises(runtime_module.RuntimeError, match="requires Linux containers"):
        runtime.assert_platform_compatible(server)


def test_container_hook_uses_shared_platform_normalization(monkeypatch):
    runtime = runtime_module.ContainerRuntime()
    calls = []

    def requirements(server):
        calls.append(server)
        return {"docker": {"operating_system": "win32"}}

    server = SimpleNamespace(name="platform", module=SimpleNamespace(get_platform_requirements=requirements))
    monkeypatch.setattr(runtime, "_run_check_output", lambda *_args, **_kwargs: "windows")
    report = runtime.assert_platform_compatible(server, _spec("custom-family"))
    assert report["container_os"] == "windows"
    assert report["container_os_compatible"] is True
    assert calls == [server]


def test_unavailable_daemon_stops_start_before_image_work(monkeypatch):
    runtime = runtime_module.ContainerRuntime()
    monkeypatch.setattr(runtime_module, "_get_module_runtime_requirements", lambda _server: {})
    monkeypatch.setattr(runtime_module, "get_container_spec", lambda *_args, **_kwargs: _spec())
    calls = []

    def docker(command, text=False):
        calls.append(command)
        raise runtime_module.RuntimeError("Cannot connect to the Docker daemon")

    monkeypatch.setattr(runtime, "_run_check_output", docker)
    with pytest.raises(runtime_module.RuntimeError, match="Cannot connect"):
        runtime.start(SimpleNamespace(name="platform"))
    assert calls == [INFO_COMMAND]
