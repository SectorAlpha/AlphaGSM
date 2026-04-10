"""Unit tests for runtime metadata resolution and Docker command assembly."""

import os
from types import SimpleNamespace

import pytest

import server.runtime as runtime_module


class FakeSection(dict):
    """Minimal settings section stub for runtime config tests."""

    def getsection(self, key):
        return self.get(key, FakeSection())


class DummyServer:
    """Minimal server stub for runtime tests."""

    def __init__(self, name="alpha", module=None, data=None):
        self.name = name
        self.module = module or SimpleNamespace()
        self.data = {} if data is None else data


def _set_runtime_backend(monkeypatch, backend):
    """Override the configured runtime backend for one test."""

    monkeypatch.setattr(
        runtime_module.settings,
        "_user",
        FakeSection({"runtime": FakeSection({"backend": backend})}),
        raising=False,
    )


def test_resolve_runtime_metadata_uses_family_defaults_and_java_alias(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 17,
        }
    )
    server = DummyServer(module=module)

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["runtime"] == "docker"
    assert metadata["runtime_family"] == "java"
    assert metadata["image"] == "ghcr.io/sectoralpha/alphagsm-java-runtime:2026-04"
    assert metadata["java_major"] == 17
    assert metadata["container_name"] == "alphagsm-alpha"
    assert metadata["network_mode"] == "bridge"
    assert metadata["stop_mode"] == "exec-console"
    assert metadata["env"] == {}
    assert metadata["mounts"] == []
    assert metadata["ports"] == []


def test_build_steamcmd_linux_runtime_requirements_uses_shared_defaults():
    server = DummyServer(data={"dir": "/srv/game/", "port": 27015})

    requirements = runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(("port", "udp"),),
    )

    assert requirements == {
        "engine": "docker",
        "family": "steamcmd-linux",
        "mounts": [
            {"source": "/srv/game/", "target": "/srv/server", "mode": "rw"}
        ],
        "ports": [
            {"host": 27015, "container": 27015, "protocol": "udp"}
        ],
    }


def test_build_container_spec_uses_get_start_command_and_shared_mounts(tmp_path):
    exe = tmp_path / "server.bin"
    exe.write_text("", encoding="utf-8")
    server = DummyServer(
        data={"dir": str(tmp_path) + "/", "exe_name": "server.bin", "port": 27015}
    )

    spec = runtime_module.build_container_spec(
        server,
        family="quake-linux",
        get_start_command=lambda current_server: (
            ["./server.bin", "+set", "port", "27015"],
            current_server.data["dir"],
        ),
        port_definitions=(("port", "udp"),),
        stdin_open=True,
    )

    assert spec["working_dir"] == "/srv/server"
    assert spec["stdin_open"] is True
    assert spec["command"][0] == "./server.bin"
    assert spec["mounts"] == [
        {"source": str(tmp_path) + "/", "target": "/srv/server", "mode": "rw"}
    ]
    assert spec["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"}
    ]


def test_infer_port_definitions_normalizes_runtime_family_aliases():
    server = DummyServer(data={"port": 25565})

    definitions = runtime_module.infer_port_definitions(server, family="minecraft")

    assert definitions == [{"key": "port", "protocol": "tcp"}]


def test_resolve_runtime_metadata_keeps_process_until_runtime_backend_is_enabled(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 17,
        }
    )
    server = DummyServer(module=module)

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata == {"runtime": "process"}


def test_container_runtime_start_builds_docker_run_command(monkeypatch):
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": "ghcr.io/sectoralpha/alphagsm-java-runtime:2026-04",
            "network_mode": "bridge",
            "working_dir": "/srv/server",
            "stdin_open": True,
            "env": {
                "ALPHAGSM_JAVA_MAJOR": "17",
                "ALPHAGSM_SERVER_JAR": "minecraft_server.jar",
            },
            "mounts": [
                {
                    "source": "/srv/host",
                    "target": "/srv/server",
                    "mode": "rw",
                }
            ],
            "ports": [
                {"host": 25565, "container": 25565, "protocol": "tcp"},
            ],
            "command": ["sh", "-lc", "exec java -jar \"$ALPHAGSM_SERVER_JAR\" nogui"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    observed = {}

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed["cmd"] = cmd
        return "container-id\n" if text else b"container-id\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.start(server)

    cmd = observed["cmd"]
    assert cmd[:4] == ["docker", "run", "-d", "-i"]
    assert "--name" in cmd and "alphagsm-alpha" in cmd
    assert "--network" in cmd and "bridge" in cmd
    assert "-w" in cmd and "/srv/server" in cmd
    assert "-e" in cmd and "ALPHAGSM_JAVA_MAJOR=17" in cmd
    assert "-e" in cmd and "ALPHAGSM_SERVER_JAR=minecraft_server.jar" in cmd
    assert "-v" in cmd and "/srv/host:/srv/server:rw" in cmd
    assert "-p" in cmd and "25565:25565/tcp" in cmd
    assert "ghcr.io/sectoralpha/alphagsm-java-runtime:2026-04" in cmd
    assert cmd[-3:] == ["sh", "-lc", "exec java -jar \"$ALPHAGSM_SERVER_JAR\" nogui"]


def test_container_runtime_send_input_uses_exec_console_mode(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(
        data={
            "runtime": "docker",
            "container_name": "alphagsm-alpha",
            "stop_mode": "exec-console",
        }
    )
    runtime = runtime_module.ContainerRuntime()
    observed = {}

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed["cmd"] = cmd
        return ""

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.send_input(server, "\nstop\n")

    cmd = observed["cmd"]
    assert cmd[:4] == ["docker", "exec", "alphagsm-alpha", "sh"]
    assert "/proc/1/fd/0" in cmd[-1]


def test_sync_runtime_metadata_persists_resolved_fields(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
        }
    )

    class _Store(dict):
        def __init__(self):
            super().__init__()
            self.saved = 0

        def save(self):
            self.saved += 1

    server = DummyServer(module=module, data=_Store())

    changed = runtime_module.sync_runtime_metadata(server, save=True)

    assert changed is True
    assert server.data["runtime"] == "docker"
    assert server.data["runtime_family"] == "java"
    assert server.data["java_major"] == 21
    assert server.data.saved == 1


def test_sync_runtime_metadata_removes_stale_docker_fields_when_process_runtime_is_selected(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")

    class _Store(dict):
        def __init__(self):
            super().__init__(
                runtime="docker",
                runtime_family="minecraft",
                image="ghcr.io/sectoralpha/alphagsm-java-runtime:2026-04",
                java_major=21,
                container_name="alphagsm-alpha",
            )
            self.saved = 0

        def save(self):
            self.saved += 1

    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
        }
    )
    server = DummyServer(module=module, data=_Store())

    changed = runtime_module.sync_runtime_metadata(server, save=True)

    assert changed is True
    assert server.data == {"runtime": "process"}
    assert server.data.saved == 1


def test_resolve_runtime_metadata_normalizes_legacy_family_aliases(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "minecraft",
            "java": 17,
        }
    )
    server = DummyServer(module=module)

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["runtime_family"] == "java"
    assert metadata["image"] == "ghcr.io/sectoralpha/alphagsm-java-runtime:2026-04"


def test_ensure_runtime_hooks_adds_defaults_for_plain_module(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        __name__="gamemodules.plainserver",
        get_start_command=lambda server: (["./plainserver", "--port", "7777"], "/srv/plain"),
    )
    server = DummyServer(
        module=module,
        data={
            "dir": "/srv/plain",
            "port": 7777,
        },
    )

    runtime_module.ensure_runtime_hooks(module)
    metadata = runtime_module.resolve_runtime_metadata(server)
    spec = runtime_module.get_container_spec(server)

    assert callable(module.get_runtime_requirements)
    assert callable(module.get_container_spec)
    assert metadata["runtime"] == "docker"
    assert metadata["runtime_family"] == "steamcmd-linux"
    assert metadata["image"] == "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:2026-04"
    assert spec["working_dir"] == "/srv/server"
    assert spec["mounts"] == [
        {"source": "/srv/plain", "target": "/srv/server", "mode": "rw"}
    ]
    assert spec["ports"] == [
        {"host": 7777, "container": 7777, "protocol": "udp"},
        {"host": 7777, "container": 7777, "protocol": "tcp"},
    ]
    assert spec["command"] == ["./plainserver", "--port", "7777"]


def test_get_container_spec_mounts_external_symlink_target(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    server_root = tmp_path / "server"
    cache_root = tmp_path / "downloads" / "cache"
    server_root.mkdir(parents=True)
    cache_root.mkdir(parents=True)
    jar_path = cache_root / "minecraft_server.jar"
    jar_path.write_text("jar", encoding="utf-8")
    os.symlink(jar_path, server_root / "minecraft_server.jar")

    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 25,
        },
        get_container_spec=lambda server: {
            "working_dir": "/srv/server",
            "stdin_open": True,
            "env": {},
            "mounts": [
                {
                    "source": str(server_root) + "/",
                    "target": "/srv/server",
                    "mode": "rw",
                }
            ],
            "ports": [],
            "command": ["java", "-jar", "minecraft_server.jar"],
        },
    )
    server = DummyServer(
        module=module,
        data={"dir": str(server_root) + "/", "exe_name": "minecraft_server.jar"},
    )

    spec = runtime_module.get_container_spec(server)

    assert spec["mounts"] == [
        {"source": str(server_root) + "/", "target": "/srv/server", "mode": "rw"},
        {"source": str(cache_root), "target": str(cache_root), "mode": "ro"},
    ]


def test_inferred_runtime_requirements_use_wine_proton_for_windows_binaries(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(__name__="gamemodules.windowsserver")
    server = DummyServer(
        module=module,
        data={
            "dir": "/srv/windows",
            "exe_name": "Server.exe",
            "port": 27015,
        },
    )

    requirements = runtime_module.infer_runtime_requirements(server, module=module)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "wine-proton"
    assert requirements["mounts"] == [
        {"source": "/srv/windows", "target": "/srv/server", "mode": "rw"}
    ]
    assert requirements["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27015, "container": 27015, "protocol": "tcp"},
    ]


def test_resolve_query_host_uses_container_ip_for_docker_runtime(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
            "container_name": "alphagsm-alpha",
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(
        runtime_module.sp,
        "check_output",
        lambda *args, **kwargs: "172.18.0.7\n",
    )

    assert runtime_module.resolve_query_host(server) == "172.18.0.7"


def test_resolve_query_host_prefers_explicit_public_ip(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(
        data={"runtime": "docker", "publicip": "192.168.1.50"},
    )

    assert runtime_module.resolve_query_host(server) == "192.168.1.50"


def test_container_runtime_kill_stops_then_removes_container(monkeypatch):
    server = DummyServer(
        data={
            "runtime": "docker",
            "container_name": "alphagsm-alpha",
        }
    )
    runtime = runtime_module.ContainerRuntime()
    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        return ""

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.kill(server)

    assert observed == [
        ["docker", "stop", "--time", "10", "alphagsm-alpha"],
        ["docker", "rm", "-f", "alphagsm-alpha"],
    ]
