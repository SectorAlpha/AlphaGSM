"""Container memory and CPU limits, including the Java heap default."""

from types import SimpleNamespace

import pytest

import server.runtime as runtime_module


JAVA_RUNTIME_IMAGE = runtime_module.default_runtime_image("java")


class FakeSection(dict):
    def getsection(self, key):
        return self.get(key, FakeSection())


def _docker_server(data):
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": JAVA_RUNTIME_IMAGE,
            "runtime_family": "java",
            "network_mode": "bridge",
            "working_dir": "/srv/server",
            "stdin_open": True,
            "command": ["sh", "-lc", 'exec java -jar "$ALPHAGSM_SERVER_JAR" nogui'],
        }
    )
    return SimpleNamespace(name="alpha", module=module, data=data)


def _run(monkeypatch, server):
    monkeypatch.setattr(
        runtime_module.settings,
        "_user",
        FakeSection({"runtime": FakeSection({"backend": "docker"})}),
        raising=False,
    )
    observed = []

    def fake_check_output(cmd, stderr=None, shell=False, text=False):
        del stderr, shell
        observed.append(cmd)
        if cmd == ["docker", "info", "--format", "{{.OSType}}"]:
            return "linux\n" if text else b"linux\n"
        if cmd[:3] == ["docker", "image", "inspect"]:
            return "image\n" if text else b"image\n"
        return "id\n" if text else b"id\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", fake_check_output)
    runtime_module.ContainerRuntime().start(server)
    return observed[-1]


def test_memory_and_cpu_limits_are_validated():
    assert runtime_module.normalize_memory_limit("2G") == "2g"
    assert runtime_module.normalize_cpu_limit("1.5") == "1.5"
    assert runtime_module.java_heap_megabytes("2g") == 1536
    with pytest.raises(runtime_module.RuntimeError, match="64m"):
        runtime_module.normalize_memory_limit("1m")
    with pytest.raises(runtime_module.RuntimeError, match="cpus"):
        runtime_module.normalize_cpu_limit("0")


def test_docker_run_applies_limits_and_default_java_heap(monkeypatch):
    command = _run(monkeypatch, _docker_server({"memory": "2g", "cpus": "1.5"}))

    assert command[command.index("--memory") + 1] == "2g"
    assert command[command.index("--cpus") + 1] == "1.5"
    assert 'exec java -Xmx1536m -jar "$ALPHAGSM_SERVER_JAR" nogui' in command


def test_explicit_java_heap_is_left_unchanged(monkeypatch):
    server = _docker_server({"memory": "2g"})
    server.module.get_container_spec = lambda server: {
        "container_name": "alphagsm-alpha",
        "image": JAVA_RUNTIME_IMAGE,
        "runtime_family": "java",
        "command": ["java", "-Xmx512m", "-jar", "server.jar"],
    }
    command = _run(monkeypatch, server)

    assert command.count("-Xmx512m") == 1
    assert "-Xmx1536m" not in command
