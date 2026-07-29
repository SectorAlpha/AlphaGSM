"""Unit tests for runtime metadata resolution and Docker command assembly."""

import os
from types import SimpleNamespace

import pytest

import server.runtime as runtime_module


JAVA_RUNTIME_IMAGE = runtime_module.default_runtime_image("java")
STEAMCMD_RUNTIME_IMAGE = runtime_module.default_runtime_image("steamcmd-linux")


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


def _set_manager_state_root(monkeypatch, tmp_path):
    """Configure and return a safe manager-owned runtime HOME path."""

    manager_root = tmp_path / "manager"
    manager_root.mkdir(mode=0o700)
    monkeypatch.setenv("ALPHAGSM_HOME", str(manager_root))
    return manager_root, manager_root / "runtime" / "alpha" / "home"


def _create_secure_runtime_home(home_source, *, create_home=True):
    """Create manager state components with the production ownership mode."""

    runtime_root = home_source.parent.parent
    runtime_root.mkdir(mode=0o700)
    home_source.parent.mkdir(mode=0o700)
    if create_home:
        home_source.mkdir(mode=0o700)


def _host_user_module(home_source, *, home_mode="rw", include_home=True, nested_mount=False):
    """Return a representative host-user Docker module for runtime tests."""

    mounts = []
    if include_home:
        mounts.append(
            {
                "source": str(home_source),
                "target": "/home/alphagsm",
                "mode": home_mode,
            }
        )
    if nested_mount:
        mounts.append(
            {
                "source": "/srv/sdk64",
                "target": "/home/alphagsm/.steam/sdk64",
                "mode": "ro",
            }
        )
    return SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
        },
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "network_mode": "bridge",
            "stop_mode": "exec-console",
            "working_dir": "/srv/server",
            "stdin_open": True,
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
            "env": {"HOME": "/home/alphagsm"},
            "mounts": mounts,
            "ports": [],
            "command": ["./server"],
        },
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
    assert metadata["image"] == JAVA_RUNTIME_IMAGE
    assert metadata["java_major"] == 17
    assert metadata["container_name"] == "alphagsm-alpha"
    assert metadata["network_mode"] == "bridge"
    assert metadata["stop_mode"] == "docker-stop"
    assert metadata["env"] == {}
    assert metadata["mounts"] == []
    assert metadata["ports"] == []


@pytest.mark.parametrize(
    ("family", "override_env", "override_image"),
    (
        ("steamcmd-linux", "ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX", "ghcr.io/example/steamcmd:ci"),
        ("java", "ALPHAGSM_BACKEND_DOCKER_IMAGE_JAVA", "ghcr.io/example/java:ci"),
    ),
)
def test_resolve_runtime_metadata_uses_ci_family_image_override_when_image_is_default(
    monkeypatch, family, override_env, override_image
):
    _set_runtime_backend(monkeypatch, "docker")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv(override_env, override_image)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": family,
        }
    )
    server = DummyServer(module=module)

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["image"] == override_image


def test_resolve_runtime_metadata_keeps_explicit_image_over_ci_family_override(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX",
        "ghcr.io/example/steamcmd:ci",
    )
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "steamcmd-linux",
        }
    )
    server = DummyServer(
        module=module,
        data={"image": "ghcr.io/example/steamcmd:explicit"},
    )

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["image"] == "ghcr.io/example/steamcmd:explicit"


def test_resolve_runtime_metadata_preserves_explicit_container_name(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "simple-tcp",
        }
    )
    server = DummyServer(
        module=module,
        data={"runtime": "docker", "container_name": "alphagsm-custom-alpha"},
    )

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["container_name"] == "alphagsm-custom-alpha"


def test_resolve_runtime_metadata_raises_stale_java_major_for_new_minecraft_versions(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
            "env": {
                "ALPHAGSM_JAVA_MAJOR": "21",
                "ALPHAGSM_SERVER_JAR": "minecraft_server.jar",
            },
        }
    )
    server = DummyServer(module=module, data={"version": "26.1.2"})

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["java_major"] == 25
    assert metadata["env"]["ALPHAGSM_JAVA_MAJOR"] == "25"
    assert metadata["env"]["ALPHAGSM_SERVER_JAR"] == "minecraft_server.jar"


def test_resolve_runtime_metadata_migrates_stale_java_exec_console_stop_mode(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
        }
    )
    server = DummyServer(module=module, data={"stop_mode": "exec-console"})

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["stop_mode"] == "docker-stop"


def test_resolve_runtime_metadata_keeps_java_default_stop_mode_for_interactive_specs(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
        },
        get_container_spec=lambda server: {
            "image": "eclipse-temurin:25-jre",
            "command": ["java", "-jar", "minecraft_server.jar"],
            "stop_mode": "exec-console",
            "stdin_open": True,
            "tty": True,
        },
    )
    server = DummyServer(module=module, data={"stop_mode": "exec-console"})

    metadata = runtime_module.resolve_runtime_metadata(server)

    assert metadata["stop_mode"] == "docker-stop"


def test_build_steamcmd_linux_runtime_requirements_uses_shared_defaults(monkeypatch):
    monkeypatch.setattr(runtime_module, "_steamcmd_sdk_mounts", lambda: [])
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


def test_build_runtime_requirements_supports_derived_port_offsets(monkeypatch):
    monkeypatch.setattr(runtime_module, "_steamcmd_sdk_mounts", lambda: [])
    server = DummyServer(data={"dir": "/srv/game/", "port": 26900})

    requirements = runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(
            {"key": "port", "protocol": "tcp"},
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "udp", "offset": 1},
            {"key": "port", "protocol": "udp", "offset": 2},
            {"key": "port", "protocol": "udp", "offset": 3},
        ),
    )

    assert requirements["ports"] == [
        {"host": 26900, "container": 26900, "protocol": "tcp"},
        {"host": 26900, "container": 26900, "protocol": "udp"},
        {"host": 26901, "container": 26901, "protocol": "udp"},
        {"host": 26902, "container": 26902, "protocol": "udp"},
        {"host": 26903, "container": 26903, "protocol": "udp"},
    ]


def test_build_port_specs_is_the_public_derived_port_api():
    server = DummyServer(data={"port": 26900})

    ports = runtime_module.build_port_specs(
        server,
        (
            {"key": "port", "protocol": "udp"},
            {"key": "port", "offset": 3, "protocol": "tcp"},
        ),
    )

    assert ports == [
        {"host": 26900, "container": 26900, "protocol": "udp"},
        {"host": 26903, "container": 26903, "protocol": "tcp"},
    ]


def test_build_steamcmd_linux_runtime_requirements_adds_steam_sdk_mounts(monkeypatch, tmp_path):
    steamcmd_root = tmp_path / "Steam"
    linux64 = steamcmd_root / "linux64"
    linux32 = steamcmd_root / "linux32"
    linux64.mkdir(parents=True)
    linux32.mkdir(parents=True)
    (linux64 / "steamclient.so").write_text("64", encoding="utf-8")
    (linux32 / "steamclient.so").write_text("32", encoding="utf-8")
    monkeypatch.setattr(runtime_module.steamcmd_module, "STEAMCMD_DIR", str(steamcmd_root))

    server = DummyServer(data={"dir": "/srv/game/", "port": 27015})

    requirements = runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(("port", "udp"),),
    )

    assert requirements["mounts"] == [
        {"source": "/srv/game/", "target": "/srv/server", "mode": "rw"},
        {"source": str(linux64), "target": "/root/.steam/sdk64", "mode": "ro"},
        {
            "source": str(linux64),
            "target": "/root/.steam/steamcmd/linux64",
            "mode": "ro",
        },
        {"source": str(linux32), "target": "/root/.steam/sdk32", "mode": "ro"},
        {
            "source": str(linux32),
            "target": "/root/.steam/steamcmd/linux32",
            "mode": "ro",
        },
    ]


def test_build_steamcmd_requirements_use_opted_in_home_for_sdk_and_runtime_data(
    monkeypatch, tmp_path
):
    steamcmd_root = tmp_path / "Steam"
    linux64 = steamcmd_root / "linux64"
    linux32 = steamcmd_root / "linux32"
    linux64.mkdir(parents=True)
    linux32.mkdir(parents=True)
    (linux64 / "steamclient.so").write_text("64", encoding="utf-8")
    (linux32 / "steamclient.so").write_text("32", encoding="utf-8")
    monkeypatch.setattr(runtime_module.steamcmd_module, "STEAMCMD_DIR", str(steamcmd_root))
    install_dir = tmp_path / "thefront"
    install_dir.mkdir()
    server = DummyServer(data={"dir": str(install_dir), "port": 7777})
    _manager_root, runtime_home = _set_manager_state_root(monkeypatch, tmp_path)

    requirements = runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        extra={
            "run_as_host_user": True,
            "container_home": "/home/custom-front",
        },
    )

    assert requirements["run_as_host_user"] is True
    assert requirements["container_home"] == "/home/custom-front"
    assert requirements["env"]["HOME"] == "/home/custom-front"
    assert requirements["mounts"] == [
        {"source": str(install_dir), "target": "/srv/server", "mode": "rw"},
        {
            "source": str(runtime_home),
            "target": "/home/custom-front",
            "mode": "rw",
        },
        {"source": str(linux64), "target": "/home/custom-front/.steam/sdk64", "mode": "ro"},
        {
            "source": str(linux64),
            "target": "/home/custom-front/.steam/steamcmd/linux64",
            "mode": "ro",
        },
        {"source": str(linux32), "target": "/home/custom-front/.steam/sdk32", "mode": "ro"},
        {
            "source": str(linux32),
            "target": "/home/custom-front/.steam/steamcmd/linux32",
            "mode": "ro",
        },
    ]
    assert install_dir not in runtime_home.parents


def test_build_runtime_requirements_preserves_explicit_module_home(monkeypatch, tmp_path):
    install_dir = tmp_path / "server"
    install_dir.mkdir()
    server = DummyServer(data={"dir": str(install_dir)})
    _manager_root, runtime_home = _set_manager_state_root(monkeypatch, tmp_path)

    requirements = runtime_module.build_runtime_requirements(
        server,
        family="simple-tcp",
        env={"HOME": "/opt/module-home"},
        extra={"run_as_host_user": True},
    )

    assert requirements["container_home"] == "/opt/module-home"
    assert requirements["env"]["HOME"] == "/opt/module-home"
    assert requirements["mounts"][-1] == {
        "source": str(runtime_home),
        "target": "/opt/module-home",
        "mode": "rw",
    }


def test_get_container_spec_normalizes_string_mounts_and_mode_tokens(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "simple-tcp",
        },
        get_container_spec=lambda server: {
            "mounts": ["/srv/source:/srv/server/:ro,Z"],
            "command": ["./server"],
            "working_dir": "/srv/server",
        },
    )
    server = DummyServer(module=module, data={"runtime": "docker"})

    spec = runtime_module.get_container_spec(server)

    assert spec["mounts"] == [
        {"source": "/srv/source", "target": "/srv/server", "mode": "ro,Z"}
    ]


def test_get_container_spec_rejects_duplicate_normalized_mount_targets(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "simple-tcp",
        },
        get_container_spec=lambda server: {
            "mounts": [
                {"source": "/srv/one", "target": "/srv/server", "mode": "rw"},
                "/srv/two:/srv/server/:ro,Z",
            ],
            "command": ["./server"],
            "working_dir": "/srv/server",
        },
    )
    server = DummyServer(module=module, data={"runtime": "docker"})

    with pytest.raises(runtime_module.RuntimeError, match="Duplicate container mount target"):
        runtime_module.get_container_spec(server)


def test_infer_minecraft_java_major_supports_new_26_x_version_scheme():
    assert runtime_module.infer_minecraft_java_major("26.1.2") == 25


def test_default_runtime_images_use_latest_tag():
    assert JAVA_RUNTIME_IMAGE.endswith(":latest")
    assert STEAMCMD_RUNTIME_IMAGE.endswith(":latest")


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
        tty=True,
    )

    assert spec["working_dir"] == "/srv/server"
    assert spec["stdin_open"] is True
    assert spec["command"][0] == "./server.bin"
    assert spec["tty"] is True
    assert spec["mounts"] == [
        {"source": str(tmp_path) + "/", "target": "/srv/server", "mode": "rw"}
    ]
    assert spec["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"}
    ]


def test_build_container_spec_maps_nested_host_workdir_into_container(tmp_path):
    nested_dir = tmp_path / "PalServer"
    nested_dir.mkdir()
    exe = nested_dir / "PalServer.sh"
    exe.write_text("", encoding="utf-8")
    server = DummyServer(
        data={"dir": str(tmp_path) + "/", "exe_name": "PalServer.sh", "port": 8211}
    )

    spec = runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=lambda _current_server: (
            ["./PalServer.sh", "-port=8211"],
            str(nested_dir),
        ),
        port_definitions=(("port", "udp"),),
    )

    assert spec["working_dir"] == "/srv/server/PalServer"
    assert spec["command"] == ["./PalServer.sh", "-port=8211"]


def test_build_container_spec_recovers_nested_executable_from_install_root(tmp_path):
    install_root = tmp_path / "valheim"
    nested_dir = install_root / "linux64"
    nested_dir.mkdir(parents=True)
    exe = nested_dir / "valheim_server.x86_64"
    exe.write_text("", encoding="utf-8")
    server = DummyServer(
        data={"dir": str(install_root) + "/", "exe_name": "valheim_server.x86_64", "port": 2456}
    )

    spec = runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=lambda _current_server: (
            ["./valheim_server.x86_64", "-port", "2456"],
            str(install_root),
        ),
        port_definitions=(("port", "udp"),),
    )

    assert spec["working_dir"] == "/srv/server/linux64"
    assert spec["command"] == ["./valheim_server.x86_64", "-port", "2456"]


def test_build_container_spec_prefers_shallowest_nested_executable_match(tmp_path):
    install_root = tmp_path / "valheim"
    nested_dir = install_root / "linux64"
    deeper_dir = install_root / "debug" / "linux64"
    nested_dir.mkdir(parents=True)
    deeper_dir.mkdir(parents=True)
    (nested_dir / "valheim_server.x86_64").write_text("", encoding="utf-8")
    (deeper_dir / "valheim_server.x86_64").write_text("", encoding="utf-8")
    server = DummyServer(
        data={"dir": str(install_root) + "/", "exe_name": "valheim_server.x86_64", "port": 2456}
    )

    spec = runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=lambda _current_server: (
            ["./valheim_server.x86_64", "-port", "2456"],
            str(install_root),
        ),
        port_definitions=(("port", "udp"),),
    )

    assert spec["working_dir"] == "/srv/server/linux64"
    assert spec["command"] == ["./valheim_server.x86_64", "-port", "2456"]


def test_build_container_spec_maps_external_launcher_workdir_into_added_mount(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_module, "_steamcmd_sdk_mounts", lambda: [])
    server_root = tmp_path / "server"
    cache_root = tmp_path / "downloads" / "cache"
    server_root.mkdir(parents=True)
    cache_root.mkdir(parents=True)
    target = cache_root / "DedicatedServerCmd"
    target.write_text("", encoding="utf-8")
    os.symlink(target, server_root / "DedicatedServerCmd")
    server = DummyServer(
        data={"dir": str(server_root) + "/", "exe_name": "DedicatedServerCmd", "port": 27015}
    )

    spec = runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=lambda _current_server: (
            ["./DedicatedServerCmd"],
            str(cache_root),
        ),
        port_definitions=(("port", "udp"),),
    )

    assert spec["working_dir"] == str(cache_root)
    assert spec["mounts"] == [
        {"source": str(server_root) + "/", "target": "/srv/server", "mode": "rw"},
        {"source": str(cache_root), "target": str(cache_root), "mode": "ro"},
    ]
    assert spec["command"] == ["./DedicatedServerCmd"]


def test_get_container_spec_remaps_recovered_host_workdir_back_into_container(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    install_root = tmp_path / "valheim"
    nested_dir = install_root / "linux64"
    nested_dir.mkdir(parents=True)
    (nested_dir / "valheim_server.x86_64").write_text("", encoding="utf-8")
    module = SimpleNamespace(
        get_runtime_requirements=lambda _server: {
            "engine": "docker",
            "family": "steamcmd-linux",
            "mounts": [
                {"source": str(install_root) + "/", "target": "/srv/server", "mode": "rw"}
            ],
        },
        get_container_spec=lambda _server: {
            "working_dir": "/srv/server",
            "mounts": [
                {"source": str(install_root) + "/", "target": "/srv/server", "mode": "rw"}
            ],
            "ports": [],
            "command": ["./valheim_server.x86_64", "-port", "2456"],
        },
    )
    server = DummyServer(
        module=module,
        data={"dir": str(install_root) + "/", "exe_name": "valheim_server.x86_64", "port": 2456},
    )

    spec = runtime_module.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server/linux64"
    assert spec["command"] == ["./valheim_server.x86_64", "-port", "2456"]


def test_get_container_spec_mounts_external_symlinked_parent_for_executable(tmp_path, monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    install_root = tmp_path / "install"
    install_root.mkdir()
    external_root = tmp_path / "external"
    target_dir = external_root / "ShooterGame" / "Binaries" / "Linux"
    target_dir.mkdir(parents=True)
    (target_dir / "ShooterGameServer").write_text("", encoding="utf-8")
    os.symlink(external_root / "ShooterGame", install_root / "ShooterGame")

    module = SimpleNamespace(
        get_runtime_requirements=lambda _server: {
            "engine": "docker",
            "family": "steamcmd-linux",
            "mounts": [
                {"source": str(install_root) + "/", "target": "/srv/server", "mode": "rw"}
            ],
        },
        get_container_spec=lambda _server: {
            "working_dir": "/srv/server",
            "command": ["./ShooterGame/Binaries/Linux/ShooterGameServer"],
        },
    )
    server = DummyServer(
        module=module,
        data={
            "dir": str(install_root) + "/",
            "exe_name": "ShooterGame/Binaries/Linux/ShooterGameServer",
        },
    )

    spec = runtime_module.get_container_spec(server)

    assert spec["mounts"] == [
        {"source": str(install_root) + "/", "target": "/srv/server", "mode": "rw"},
        {"source": str(external_root), "target": str(external_root), "mode": "ro"},
    ]


def test_build_container_spec_normalizes_java_runtime_command_and_disables_tty(tmp_path):
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    server = DummyServer(
        data={
            "dir": str(server_dir) + "/",
            "exe_name": "minecraft_server.jar",
            "port": 25565,
        }
    )

    spec = runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=lambda current_server: (
            ["/host/java-wrapper.sh", "-jar", current_server.data["exe_name"], "nogui"],
            current_server.data["dir"],
        ),
        port_definitions=(("port", "tcp"),),
        stdin_open=True,
        tty=True,
        env={"ALPHAGSM_SERVER_JAR": "minecraft_server.jar"},
    )

    assert spec["command"] == ["java", "-jar", "minecraft_server.jar", "nogui"]
    assert spec["tty"] is True


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
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": JAVA_RUNTIME_IMAGE,
            "runtime_family": "java",
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

    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return "existing-image\n" if text else b"existing-image\n"
        return "container-id\n" if text else b"container-id\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.start(server)

    assert observed[0][:3] == ["docker", "image", "inspect"]
    cmd = observed[-1]
    assert cmd[:4] == ["docker", "run", "-d", "-i"]
    assert "--name" in cmd and "alphagsm-alpha" in cmd
    assert "--network" in cmd and "bridge" in cmd
    assert "-w" in cmd and "/srv/server" in cmd
    assert "-e" in cmd and "ALPHAGSM_JAVA_MAJOR=17" in cmd
    assert "-e" in cmd and "ALPHAGSM_SERVER_JAR=minecraft_server.jar" in cmd
    assert "-v" in cmd and "/srv/host:/srv/server:rw" in cmd
    assert "-p" in cmd and "25565:25565/tcp" in cmd
    assert JAVA_RUNTIME_IMAGE in cmd
    assert cmd[-3:] == ["sh", "-lc", "exec java -jar \"$ALPHAGSM_SERVER_JAR\" nogui"]


def test_container_runtime_builds_default_family_image_when_missing(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "stdin_open": True,
            "env": {},
            "mounts": [],
            "ports": [],
            "command": ["./srcds_run"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            raise runtime_module.sp.CalledProcessError(1, cmd, output="missing image")
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)
    monkeypatch.setattr(runtime_module.os.path, "isfile", lambda path: True)

    runtime.start(server)

    assert observed[0][:3] == ["docker", "image", "inspect"]
    assert observed[1][:2] == ["docker", "build"]
    assert observed[1][observed[1].index("-t") + 1] == (
        STEAMCMD_RUNTIME_IMAGE
    )
    assert observed[1][-1] == runtime_module.REPO_ROOT
    assert observed[-1][:3] == ["docker", "run", "-d"]


def test_container_runtime_does_not_build_missing_custom_image(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": "custom/runtime:image",
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "stdin_open": False,
            "env": {},
            "mounts": [],
            "ports": [],
            "command": ["./srcds_run"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            raise runtime_module.sp.CalledProcessError(1, cmd, output="missing image")
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.start(server)

    assert observed[0][:3] == ["docker", "image", "inspect"]
    assert not any(cmd[:2] == ["docker", "build"] for cmd in observed)
    assert observed[-1][:3] == ["docker", "run", "-d"]


def test_runtime_doctor_report_shows_process_runtime_when_backend_is_not_enabled(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: False)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 17,
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.screen, "check_screen_exists", lambda name: True)

    report = runtime_module.get_runtime_doctor_report(server)

    assert report["configured_backend"] == "process"
    assert report["module_runtime"] == "docker"
    assert report["module_runtime_family"] == "java"
    assert report["resolved_runtime"] == "process"
    assert report["running"] is True


def test_process_host_dependency_report_rejects_stale_java_for_process_runtime(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
        }
    )
    server = DummyServer(module=module, data={"javapath": "java"})

    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: "/usr/bin/java")
    monkeypatch.setattr(
        runtime_module.sp,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="",
            stderr='openjdk version "17.0.10"\n',
            returncode=0,
        ),
    )

    report = runtime_module.get_process_host_dependency_report(server)

    assert report["applicable"] is True
    assert report["ok"] is False
    assert report["requirements"][0]["id"] == "java"
    assert report["requirements"][0]["installed_major"] == 17
    assert "Java 21+ is required" in report["requirements"][0]["error"]


def test_assert_host_install_requirements_raises_for_missing_generic_dependency(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "host_dependencies": [
                {"id": "dotnet", "display_name": ".NET", "command": "dotnet"}
            ]
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: None)

    with pytest.raises(runtime_module.RuntimeError, match="Can't setup server"):
        runtime_module.assert_host_install_requirements(server, phase="setup")


def test_assert_host_install_requirements_includes_linux_install_hint_and_docker_fallback(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_host_platform", lambda: "linux")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "host_dependencies": [
                {
                    "id": "xvfb-run",
                    "display_name": "xvfb-run",
                    "command": "xvfb-run",
                    "install_hints": {
                        "linux": "Install the host package 'xvfb' before launching this server locally.",
                    },
                }
            ]
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: None)

    with pytest.raises(runtime_module.RuntimeError) as exc_info:
        runtime_module.assert_host_install_requirements(server, phase="start")

    message = str(exc_info.value)
    assert "Install the host package 'xvfb'" in message
    assert "Use the Docker runtime instead" in message


def test_assert_host_install_requirements_includes_windows_install_hint(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_host_platform", lambda: "windows")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "host_dependencies": [
                {
                    "id": "java",
                    "display_name": "Java",
                    "command": "java",
                    "install_hints": {
                        "windows": "Install Java 21+ on this Windows host before starting the server locally.",
                    },
                }
            ]
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: None)

    with pytest.raises(runtime_module.RuntimeError) as exc_info:
        runtime_module.assert_host_install_requirements(server, phase="start")

    message = str(exc_info.value)
    assert "Install Java 21+ on this Windows host" in message
    assert "apt install" not in message


def test_assert_host_install_requirements_includes_macos_install_hint(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_host_platform", lambda: "macos")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "host_dependencies": [
                {
                    "id": "java",
                    "display_name": "Java",
                    "command": "java",
                    "install_hints": {
                        "macos": "Install Java 21+ on this Mac host, for example with Homebrew.",
                    },
                }
            ]
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: None)

    with pytest.raises(runtime_module.RuntimeError) as exc_info:
        runtime_module.assert_host_install_requirements(server, phase="start")

    message = str(exc_info.value)
    assert "Install Java 21+ on this Mac host" in message
    assert "Use the Docker runtime instead" in message


def test_host_dependency_report_skips_dependencies_for_other_platforms(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_host_platform", lambda: "windows")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "host_dependencies": [
                {
                    "id": "xvfb-run",
                    "display_name": "xvfb-run",
                    "command": "xvfb-run",
                    "platforms": ("linux",),
                }
            ]
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: None)

    report = runtime_module.get_process_host_dependency_report(server)

    assert report["applicable"] is True
    assert report["ok"] is True
    assert report["requirements"] == []


def test_process_host_dependency_report_accepts_first_available_alternative_command(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "host_dependencies": [
                {
                    "id": "wine-proton",
                    "display_name": "Wine or Proton-GE",
                    "command": [
                        {"label": "wine", "command": "wine"},
                        {"label": "proton", "command": "/opt/proton-ge/GE-Proton9-27/proton"},
                    ],
                }
            ]
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(
        runtime_module.shutil,
        "which",
        lambda executable: "/usr/bin/wine" if executable == "wine" else None,
    )

    report = runtime_module.get_process_host_dependency_report(server)

    assert report["applicable"] is True
    assert report["ok"] is True
    assert report["requirements"][0]["id"] == "wine-proton"
    assert report["requirements"][0]["matched_variant"] == "wine"
    assert report["requirements"][0]["resolved_path"] == "/usr/bin/wine"


def test_assert_host_install_requirements_raises_for_missing_alternative_commands(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "host_dependencies": [
                {
                    "id": "wine-proton",
                    "display_name": "Wine or Proton-GE",
                    "command": [
                        {"label": "wine", "command": "wine"},
                        {"label": "proton", "command": "proton"},
                    ],
                }
            ]
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: None)

    with pytest.raises(runtime_module.RuntimeError, match="none of these commands were found: 'wine', 'proton'"):
        runtime_module.assert_host_install_requirements(server, phase="start")


def test_process_runtime_start_checks_host_dependencies_before_launch(monkeypatch):
    runtime = runtime_module.ProcessRuntime()
    server = DummyServer(
        module=SimpleNamespace(
            get_start_command=lambda current, *args, **kwargs: (["./run-server"], "/srv/server")
        ),
    )
    events = []

    monkeypatch.setattr(
        runtime_module,
        "assert_host_install_requirements",
        lambda current, phase="run": events.append(("deps", phase)),
    )
    monkeypatch.setattr(
        runtime_module.screen,
        "start_screen",
        lambda name, command, cwd=None: events.append(("start_screen", name, command, cwd)),
    )

    runtime.start(server)

    assert events == [
        ("deps", "start"),
        ("start_screen", "alpha", ["./run-server"], "/srv/server"),
    ]


def test_runtime_doctor_report_includes_process_host_requirement_results(monkeypatch):
    _set_runtime_backend(monkeypatch, "process")
    monkeypatch.setattr(runtime_module, "_process_host_checks_supported", lambda: True)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 21,
        }
    )
    server = DummyServer(module=module)

    monkeypatch.setattr(runtime_module.screen, "check_screen_exists", lambda name: False)
    monkeypatch.setattr(runtime_module.shutil, "which", lambda executable: "/usr/bin/java")
    monkeypatch.setattr(
        runtime_module.sp,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="",
            stderr='openjdk version "17.0.10"\n',
            returncode=0,
        ),
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert report["resolved_runtime"] == "process"
    assert report["host_requirements_ok"] is False
    assert report["host_requirements"][0]["id"] == "java"


def test_runtime_doctor_report_includes_docker_runtime_health(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "simple-tcp",
        },
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "simple-tcp",
            "network_mode": "bridge",
            "stop_mode": "docker-stop",
            "working_dir": "/srv/server",
            "stdin_open": False,
            "env": {},
            "mounts": [{"source": "/srv/host", "target": "/srv/server", "mode": "rw"}],
            "ports": [{"host": 25565, "container": 25565, "protocol": "tcp"}],
            "command": ["./server"],
        },
    )
    server = DummyServer(module=module, data={"runtime": "docker"})

    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_run_check_output",
        staticmethod(lambda command, text=False: "25.0.3\n"),
    )
    monkeypatch.setattr(runtime_module.ContainerRuntime, "_image_exists", lambda self, image: True)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_container_running_state",
        lambda self, name: False,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_validate_mount_path_identity",
        lambda self, spec: None,
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert report["configured_backend"] == "docker"
    assert report["resolved_runtime"] == "docker"
    assert report["runtime_family"] == "simple-tcp"
    assert report["docker_cli"] == "25.0.3"
    assert report["image_present"] is True
    assert report["container_state"] == "stopped"
    assert report["mount_path_identity"] == "ok"
    assert report["working_dir"] == "/srv/server"
    assert report["command"] == ["./server"]
    assert report["mounts"] == [{"source": "/srv/host", "target": "/srv/server", "mode": "rw"}]
    assert report["ports"] == [{"host": 25565, "container": 25565, "protocol": "tcp"}]
    assert report["mount_count"] == 1
    assert report["port_count"] == 1


def test_runtime_doctor_reports_opted_in_user_home_and_writable_mount(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    _create_secure_runtime_home(home_source)
    home_mount = {
        "source": str(home_source),
        "target": "/home/alphagsm",
        "mode": "rw",
    }
    requirement_calls = []

    def _requirements(_server):
        requirement_calls.append(True)
        return {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
        }

    module = SimpleNamespace(
        get_runtime_requirements=_requirements,
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "network_mode": "bridge",
            "stop_mode": "exec-console",
            "working_dir": "/srv/server",
            "stdin_open": True,
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
            "env": {"HOME": "/home/alphagsm"},
            "mounts": [home_mount],
            "ports": [],
            "command": ["./TheFrontServer"],
        },
    )
    server = DummyServer(module=module, data={"runtime": "docker"})

    effective_uid = os.geteuid()
    effective_gid = os.getegid()
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_run_check_output",
        staticmethod(lambda command, text=False: "25.0.3\n"),
    )
    monkeypatch.setattr(runtime_module.ContainerRuntime, "_image_exists", lambda self, image: True)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_container_running_state",
        lambda self, name: False,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_validate_mount_path_identity",
        lambda self, spec: None,
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert requirement_calls == [True]
    assert report["run_as_host_user"] is True
    assert report["effective_user"] == f"{effective_uid}:{effective_gid}"
    assert report["home"] == "/home/alphagsm"
    assert report["container_home_mount"] == home_mount
    assert report["container_home_mount_writable"] is True
    assert report["container_home_source_writable"] is True
    assert report["container_home_source_exists"] is True
    assert report["container_home_source_creatable"] is False


def test_runtime_doctor_reports_safely_creatable_first_run_home_without_creating_it(
    monkeypatch, tmp_path
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    server = DummyServer(
        module=_host_user_module(home_source),
        data={"runtime": "docker"},
    )

    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_run_check_output",
        staticmethod(lambda command, text=False: "25.0.3\n"),
    )
    monkeypatch.setattr(runtime_module.ContainerRuntime, "_image_exists", lambda self, image: True)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_container_running_state",
        lambda self, name: None,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_validate_mount_path_identity",
        lambda self, spec: None,
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert report["container_home_source_exists"] is False
    assert report["container_home_source_creatable"] is True
    assert report["container_home_source_writable"] is False
    assert "container_home_error" not in report
    assert not home_source.exists()


@pytest.mark.parametrize(
    ("case", "expected_error"),
    (
        ("root", "effective UID is 0"),
        ("missing", "requires a writable bind mount"),
        ("read_only", "writable container HOME mount"),
        ("unsafe", "symbolic link"),
    ),
)
def test_runtime_doctor_reports_invalid_host_user_home(
    monkeypatch, tmp_path, case, expected_error
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    if case == "unsafe":
        _create_secure_runtime_home(home_source, create_home=False)
        outside_home = tmp_path / "outside-home"
        outside_home.mkdir()
        home_source.symlink_to(outside_home, target_is_directory=True)
    module = _host_user_module(
        home_source,
        home_mode="ro,Z" if case == "read_only" else "rw",
        include_home=case != "missing",
    )
    server = DummyServer(module=module, data={"runtime": "docker"})

    if case == "root":
        monkeypatch.setattr(runtime_module.os, "geteuid", lambda: 0)
        monkeypatch.setattr(runtime_module.os, "getegid", lambda: 0)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_run_check_output",
        staticmethod(lambda command, text=False: "25.0.3\n"),
    )
    monkeypatch.setattr(runtime_module.ContainerRuntime, "_image_exists", lambda self, image: True)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_container_running_state",
        lambda self, name: None,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_validate_mount_path_identity",
        lambda self, spec: None,
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert expected_error in report["container_home_error"]
    if case != "unsafe":
        assert not home_source.exists()


def test_runtime_doctor_stops_after_invalid_host_user_home_like_start(
    monkeypatch, tmp_path
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    server = DummyServer(
        module=_host_user_module(home_source, include_home=False),
        data={"runtime": "docker"},
    )

    def _unexpected_downstream(*_args, **_kwargs):
        pytest.fail("invalid HOME must fail before mount translation or Docker health")

    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "validate_mount_path_identity",
        _unexpected_downstream,
    )
    monkeypatch.setattr(
        runtime_module,
        "_validate_host_visible_host_user_home_overlap",
        _unexpected_downstream,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "docker_cli_version",
        _unexpected_downstream,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "image_exists",
        _unexpected_downstream,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "container_running_state",
        _unexpected_downstream,
    )

    report = runtime_module.get_runtime_doctor_report(server)
    runtime = runtime_module.ContainerRuntime()
    monkeypatch.setattr(runtime, "_validate_mount_path_identity", _unexpected_downstream)
    monkeypatch.setattr(runtime, "_ensure_runtime_image_available", _unexpected_downstream)
    monkeypatch.setattr(runtime, "_container_running_state", _unexpected_downstream)

    with pytest.raises(runtime_module.RuntimeError) as start_error:
        runtime.start(server)

    assert "requires a writable bind mount" in report["container_home_error"]
    assert report["container_home_error"] == str(start_error.value)
    assert "mount_path_identity" not in report
    assert "docker_cli" not in report
    assert "image_present" not in report
    assert "container_state" not in report


@pytest.mark.parametrize(
    ("requirements_opt_in", "spec_opt_in", "run_as_root", "expected_error", "spec_count"),
    (
        (True, False, False, "does not match authoritative runtime requirements", 1),
        (False, True, False, "does not match authoritative runtime requirements", 1),
        (True, False, True, "effective UID is 0", 0),
        (False, True, True, "does not match authoritative runtime requirements", 1),
    ),
)
def test_runtime_doctor_uses_authoritative_identity_requirements_once(
    monkeypatch,
    tmp_path,
    requirements_opt_in,
    spec_opt_in,
    run_as_root,
    expected_error,
    spec_count,
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    requirement_calls = []
    spec_calls = []

    def _requirements(_server):
        requirement_calls.append(True)
        return {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": requirements_opt_in,
            "container_home": "/home/alphagsm",
        }

    def _container_spec(_server):
        spec_calls.append(True)
        return {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "run_as_host_user": spec_opt_in,
            "container_home": "/home/alphagsm",
            "env": {"HOME": "/home/alphagsm"} if spec_opt_in else {},
            "mounts": [
                {
                    "source": str(home_source),
                    "target": "/home/alphagsm",
                    "mode": "rw",
                }
            ]
            if spec_opt_in
            else [],
            "ports": [],
            "command": ["./server"],
        }

    server = DummyServer(
        module=SimpleNamespace(
            get_runtime_requirements=_requirements,
            get_container_spec=_container_spec,
        ),
        data={"runtime": "docker"},
    )
    if run_as_root:
        monkeypatch.setattr(runtime_module.os, "geteuid", lambda: 0)
        monkeypatch.setattr(runtime_module.os, "getegid", lambda: 0)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_run_check_output",
        staticmethod(
            lambda *args, **kwargs: pytest.fail(
                "identity blockers must precede Docker doctor work"
            )
        ),
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert expected_error in report["container_identity_error"]
    assert report["container_home_error"] == report["container_identity_error"]
    assert requirement_calls == [True]
    assert len(spec_calls) == spec_count


def test_runtime_doctor_reports_authoritative_container_home_mismatch(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    requirement_calls = []

    def _requirements(_server):
        requirement_calls.append(True)
        return {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
        }

    server = DummyServer(
        module=SimpleNamespace(
            get_runtime_requirements=_requirements,
            get_container_spec=lambda current: {
                "container_name": "alphagsm-alpha",
                "image": STEAMCMD_RUNTIME_IMAGE,
                "runtime_family": "steamcmd-linux",
                "working_dir": "/srv/server",
                "run_as_host_user": True,
                "container_home": "/home/different",
                "env": {"HOME": "/home/different"},
                "mounts": [
                    {
                        "source": str(home_source),
                        "target": "/home/different",
                        "mode": "rw",
                    }
                ],
                "ports": [],
                "command": ["./server"],
            },
        ),
        data={"runtime": "docker"},
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_run_check_output",
        staticmethod(
            lambda *args, **kwargs: pytest.fail(
                "HOME mismatch must precede Docker doctor work"
            )
        ),
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert (
        "container_home does not match authoritative runtime requirements"
        in report["container_identity_error"]
    )
    assert requirement_calls == [True]


@pytest.mark.parametrize("missing_flag", ("O_NOFOLLOW", "O_DIRECTORY"))
def test_runtime_doctor_does_not_report_first_run_home_creatable_without_secure_open_flags(
    monkeypatch, tmp_path, missing_flag
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    server = DummyServer(
        module=_host_user_module(home_source),
        data={"runtime": "docker"},
    )

    monkeypatch.setattr(runtime_module.os, missing_flag, 0)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_run_check_output",
        staticmethod(lambda command, text=False: "25.0.3\n"),
    )
    monkeypatch.setattr(runtime_module.ContainerRuntime, "_image_exists", lambda self, image: True)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_container_running_state",
        lambda self, name: None,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_validate_mount_path_identity",
        lambda self, spec: None,
    )

    report = runtime_module.get_runtime_doctor_report(server)

    assert "no-follow directory traversal support" in report["container_home_error"]
    assert "container_home_source_creatable" not in report
    assert not home_source.exists()


def test_print_runtime_doctor_reports_home_mount_and_host_source_writability(
    monkeypatch, capsys
):
    server = DummyServer()
    monkeypatch.setattr(
        runtime_module,
        "get_runtime_doctor_report",
        lambda current: {
            "configured_backend": "docker",
            "resolved_runtime": "docker",
            "running": False,
            "runtime_family": "steamcmd-linux",
            "run_as_host_user": True,
            "effective_user": "1001:1002",
            "home": "/home/alphagsm",
            "container_home_mount_writable": True,
            "container_home_source_writable": True,
            "container_home_source_exists": False,
            "container_home_source_creatable": True,
        },
    )

    runtime_module.print_runtime_doctor_report(server)

    output = capsys.readouterr().out
    assert "Container HOME mount writable: yes" in output
    assert "Container HOME host source writable: yes" in output
    assert "Container HOME host source exists: no" in output
    assert "Container HOME host source safely creatable: yes" in output


def test_print_runtime_doctor_reports_spec_identity_mismatch_without_opt_in(
    monkeypatch, capsys
):
    server = DummyServer()
    mismatch = (
        "Final container spec run_as_host_user=true does not match authoritative "
        "runtime requirements run_as_host_user=false"
    )
    monkeypatch.setattr(
        runtime_module,
        "get_runtime_doctor_report",
        lambda current: {
            "configured_backend": "docker",
            "resolved_runtime": "docker",
            "running": False,
            "runtime_family": "steamcmd-linux",
            "container_identity_error": mismatch,
        },
    )

    runtime_module.print_runtime_doctor_report(server)

    assert "Container identity error: " + mismatch in capsys.readouterr().out


def test_container_runtime_removes_stale_stopped_container_before_start(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": JAVA_RUNTIME_IMAGE,
            "runtime_family": "java",
            "working_dir": "/srv/server",
            "stdin_open": False,
            "env": {},
            "mounts": [],
            "ports": [],
            "command": ["java", "-jar", "server.jar"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return "existing-image\n" if text else b"existing-image\n"
        if cmd[:3] == ["docker", "inspect", "-f"]:
            return "false\n" if text else b"false\n"
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.start(server)

    assert ["docker", "rm", "-f", "alphagsm-alpha"] in observed
    assert observed[-1][:3] == ["docker", "run", "-d"]
    assert "--user" not in observed[-1]
    assert not any(str(argument).startswith("HOME=") for argument in observed[-1])


def test_container_runtime_runs_opted_in_server_as_effective_host_user(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    install_dir = tmp_path / "thefront"
    install_dir.mkdir()
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    executable = install_dir / "TheFrontServer"
    executable.write_text("", encoding="utf-8")
    steamcmd_root = tmp_path / "Steam"
    for sdk_dir in (steamcmd_root / "linux64", steamcmd_root / "linux32"):
        sdk_dir.mkdir(parents=True)
        (sdk_dir / "steamclient.so").write_text("sdk", encoding="utf-8")
    extra = {
        "run_as_host_user": True,
        "container_home": "/home/alphagsm",
    }
    server = DummyServer(
        data={"runtime": "docker", "dir": str(install_dir), "Steam_AppID": 985050}
    )
    server.module = SimpleNamespace(
        get_runtime_requirements=lambda current: runtime_module.build_runtime_requirements(
            current,
            family="steamcmd-linux",
            extra=extra,
        ),
        get_container_spec=lambda current: runtime_module.build_container_spec(
            current,
            family="steamcmd-linux",
            get_start_command=lambda configured: (["./TheFrontServer"], configured.data["dir"]),
            extra=extra,
        ),
    )
    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return "existing-image\n" if text else b"existing-image\n"
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(runtime_module.steamcmd_module, "STEAMCMD_DIR", str(steamcmd_root))
    effective_uid = os.geteuid()
    effective_gid = os.getegid()
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime_module.ContainerRuntime().start(server)

    command = observed[-1]
    assert home_source.is_dir()
    assert (home_source / ".steam" / "sdk64").is_dir()
    assert (home_source / ".steam" / "sdk32").is_dir()
    libraryfolders = (
        home_source / ".steam" / "steam" / "steamapps" / "libraryfolders.vdf"
    )
    assert libraryfolders.read_text(encoding="utf-8") == (
        '"libraryfolders"\n'
        "{\n"
        '    "0"\n'
        "    {\n"
        '        "path" "/srv/server"\n'
        '        "apps"\n'
        "        {\n"
        '            "985050" "0"\n'
        "        }\n"
        "    }\n"
        "}\n"
    )
    assert not (home_source / "Steam" / "config" / "config.vdf").exists()
    assert not (home_source / "Steam").exists()
    assert command[:3] == ["docker", "run", "-d"]
    assert command[command.index("--user") : command.index("--user") + 2] == [
        "--user",
        f"{effective_uid}:{effective_gid}",
    ]
    assert command.index("--user") < command.index("--name")
    assert ["-e", "HOME=/home/alphagsm"] == command[
        command.index("-e") : command.index("-e") + 2
    ]
    assert ["-v", f"{home_source}:/home/alphagsm:rw"] == command[
        command.index("-v", command.index("-v") + 1) : command.index("-v", command.index("-v") + 1) + 2
    ]
    assert command.index("--user") < command.index(STEAMCMD_RUNTIME_IMAGE)
    assert "uid" not in server.data
    assert "gid" not in server.data
    assert "user" not in server.data
    assert "effective_uid" not in server.data
    assert "effective_gid" not in server.data


@pytest.mark.parametrize(
    ("requirements_opt_in", "spec_opt_in", "expects_user"),
    (
        (False, False, False),
        (True, True, True),
    ),
)
def test_container_runtime_evaluates_consistent_identity_requirements_once(
    monkeypatch,
    tmp_path,
    requirements_opt_in,
    spec_opt_in,
    expects_user,
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    requirement_calls = []

    def _requirements(_server):
        requirement_calls.append(True)
        return {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": requirements_opt_in,
            "container_home": "/home/alphagsm",
        }

    mounts = []
    if spec_opt_in:
        mounts.append(
            {
                "source": str(home_source),
                "target": "/home/alphagsm",
                "mode": "rw",
            }
        )
    module = SimpleNamespace(
        get_runtime_requirements=_requirements,
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "stdin_open": False,
            "run_as_host_user": spec_opt_in,
            "container_home": "/home/alphagsm",
            "env": {"HOME": "/home/alphagsm"} if spec_opt_in else {},
            "mounts": mounts,
            "ports": [],
            "command": ["./server"],
        },
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    observed = []

    def _fake_check_output(command, stderr=None, shell=False, text=False):
        observed.append(command)
        if command[:3] == ["docker", "inspect", "-f"]:
            raise runtime_module.RuntimeError("missing")
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "_validate_mount_path_identity",
        lambda self, spec: None,
    )

    runtime_module.ContainerRuntime().start(server)

    assert requirement_calls == [True]
    docker_run = observed[-1]
    assert ("--user" in docker_run) is expects_user


@pytest.mark.parametrize(
    ("requirements_opt_in", "spec_opt_in", "run_as_root", "expected_error", "spec_count"),
    (
        (True, False, False, "does not match authoritative runtime requirements", 1),
        (False, True, False, "does not match authoritative runtime requirements", 1),
        (True, False, True, "effective UID is 0", 0),
        (False, True, True, "does not match authoritative runtime requirements", 1),
    ),
)
def test_container_runtime_rejects_identity_mismatch_with_single_requirement_evaluation(
    monkeypatch,
    tmp_path,
    requirements_opt_in,
    spec_opt_in,
    run_as_root,
    expected_error,
    spec_count,
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    requirement_calls = []
    spec_calls = []

    def _requirements(_server):
        requirement_calls.append(True)
        return {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": requirements_opt_in,
            "container_home": "/home/alphagsm",
        }

    def _container_spec(_server):
        spec_calls.append(True)
        mounts = []
        if spec_opt_in:
            mounts.append(
                {
                    "source": str(home_source),
                    "target": "/home/alphagsm",
                    "mode": "rw",
                }
            )
        return {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "run_as_host_user": spec_opt_in,
            "container_home": "/home/alphagsm",
            "env": {"HOME": "/home/alphagsm"} if spec_opt_in else {},
            "mounts": mounts,
            "ports": [],
            "command": ["./server"],
        }

    server = DummyServer(
        module=SimpleNamespace(
            get_runtime_requirements=_requirements,
            get_container_spec=_container_spec,
        ),
        data={"runtime": "docker"},
    )
    if run_as_root:
        monkeypatch.setattr(runtime_module.os, "geteuid", lambda: 0)
        monkeypatch.setattr(runtime_module.os, "getegid", lambda: 0)
    monkeypatch.setattr(
        runtime_module.sp,
        "check_output",
        lambda *args, **kwargs: pytest.fail("identity blockers must precede Docker work"),
    )

    with pytest.raises(runtime_module.RuntimeError, match=expected_error):
        runtime_module.ContainerRuntime().start(server)

    assert requirement_calls == [True]
    assert len(spec_calls) == spec_count


def test_container_runtime_rejects_container_home_mismatch(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    requirement_calls = []

    def _requirements(_server):
        requirement_calls.append(True)
        return {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
        }

    server = DummyServer(
        module=SimpleNamespace(
            get_runtime_requirements=_requirements,
            get_container_spec=lambda current: {
                "container_name": "alphagsm-alpha",
                "image": STEAMCMD_RUNTIME_IMAGE,
                "runtime_family": "steamcmd-linux",
                "working_dir": "/srv/server",
                "run_as_host_user": True,
                "container_home": "/home/different",
                "env": {"HOME": "/home/different"},
                "mounts": [
                    {
                        "source": str(home_source),
                        "target": "/home/different",
                        "mode": "rw",
                    }
                ],
                "ports": [],
                "command": ["./server"],
            },
        ),
        data={"runtime": "docker"},
    )

    with pytest.raises(
        runtime_module.RuntimeError,
        match="container_home does not match authoritative runtime requirements",
    ):
        runtime_module.ContainerRuntime().start(server)

    assert requirement_calls == [True]


def test_container_runtime_checks_existing_state_before_creating_home(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
        },
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
            "env": {"HOME": "/home/alphagsm"},
            "mounts": [
                {
                    "source": str(home_source),
                    "target": "/home/alphagsm",
                    "mode": "rw",
                }
            ],
            "ports": [],
            "command": ["./server"],
        },
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    def _running_container(_name):
        assert not home_source.exists()
        return True

    monkeypatch.setattr(runtime, "_container_running_state", _running_container)
    monkeypatch.setattr(runtime, "_ensure_runtime_image_available", lambda spec: None)
    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)

    with pytest.raises(runtime_module.RuntimeError, match="already running"):
        runtime.start(server)

    assert not home_source.exists()


def test_container_runtime_rejects_symlinked_home_source(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    _create_secure_runtime_home(home_source, create_home=False)
    outside_home = tmp_path / "outside-home"
    outside_home.mkdir()
    home_source.symlink_to(outside_home, target_is_directory=True)
    server = DummyServer(
        module=_host_user_module(home_source),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)
    monkeypatch.setattr(
        runtime,
        "_container_running_state",
        lambda name: pytest.fail("unsafe HOME must fail before Docker inspection"),
    )

    with pytest.raises(runtime_module.RuntimeError, match="symbolic link"):
        runtime.start(server)


def test_container_runtime_rejects_symlinked_nested_home_mountpoint(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    _create_secure_runtime_home(home_source)
    outside_steam = tmp_path / "outside-steam"
    outside_steam.mkdir()
    (home_source / ".steam").symlink_to(outside_steam, target_is_directory=True)
    server = DummyServer(
        module=_host_user_module(home_source, nested_mount=True),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)
    monkeypatch.setattr(
        runtime,
        "_container_running_state",
        lambda name: pytest.fail("unsafe HOME must fail before Docker inspection"),
    )

    with pytest.raises(runtime_module.RuntimeError, match="symbolic link"):
        runtime.start(server)


def test_container_runtime_rejects_home_not_owned_by_effective_uid(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    _create_secure_runtime_home(home_source)
    server = DummyServer(
        module=_host_user_module(home_source),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()
    real_lstat = os.lstat

    def _wrong_home_owner(path, *args, **kwargs):
        result = real_lstat(path, *args, **kwargs)
        if os.path.abspath(path) == os.path.abspath(home_source):
            values = list(result)
            values[4] = os.geteuid() + 1
            return os.stat_result(values)
        return result

    monkeypatch.setattr(runtime_module.os, "lstat", _wrong_home_owner)
    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)
    monkeypatch.setattr(
        runtime,
        "_container_running_state",
        lambda name: pytest.fail("wrong HOME ownership must fail before Docker inspection"),
    )

    with pytest.raises(runtime_module.RuntimeError, match="owned by effective UID"):
        runtime.start(server)


def test_container_runtime_rejects_group_or_world_writable_home(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    _create_secure_runtime_home(home_source)
    home_source.chmod(0o770)
    server = DummyServer(
        module=_host_user_module(home_source),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)
    monkeypatch.setattr(
        runtime,
        "_container_running_state",
        lambda name: pytest.fail("unsafe HOME mode must fail before Docker inspection"),
    )

    with pytest.raises(runtime_module.RuntimeError, match="group- or world-writable"):
        runtime.start(server)


@pytest.mark.parametrize("home_mode", (0o600, 0o200))
def test_container_runtime_requires_owner_read_write_execute_on_home(
    monkeypatch, tmp_path, home_mode
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    _create_secure_runtime_home(home_source)
    home_source.chmod(home_mode)
    server = DummyServer(
        module=_host_user_module(home_source),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)
    monkeypatch.setattr(
        runtime,
        "_ensure_runtime_image_available",
        lambda spec: pytest.fail("unsafe HOME mode must fail before Docker work"),
    )

    try:
        with pytest.raises(
            runtime_module.RuntimeError,
            match="owner read, write, and execute permissions",
        ):
            runtime.start(server)
    finally:
        home_source.chmod(0o700)


def test_container_runtime_treats_ro_mode_token_list_as_read_only(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    server = DummyServer(
        module=_host_user_module(home_source, home_mode="ro,Z"),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)

    with pytest.raises(runtime_module.RuntimeError, match="writable container HOME mount"):
        runtime.start(server)

    assert not home_source.exists()


def test_container_runtime_rejects_home_nested_in_writable_content_mount(
    monkeypatch, tmp_path
):
    _set_runtime_backend(monkeypatch, "docker")
    install_dir = tmp_path / "server-content"
    install_dir.mkdir()
    manager_root = install_dir / "manager"
    manager_root.mkdir(mode=0o700)
    monkeypatch.setenv("ALPHAGSM_HOME", str(manager_root))
    server = DummyServer(data={"runtime": "docker", "dir": str(install_dir)})
    extra = {
        "run_as_host_user": True,
        "container_home": "/home/alphagsm",
    }
    server.module = SimpleNamespace(
        get_runtime_requirements=lambda current: runtime_module.build_runtime_requirements(
            current,
            family="steamcmd-linux",
            extra=extra,
        ),
        get_container_spec=lambda current: runtime_module.build_container_spec(
            current,
            family="steamcmd-linux",
            get_start_command=lambda configured: (["./server"], configured.data["dir"]),
            extra=extra,
        ),
    )
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(runtime_module, "_steamcmd_sdk_mounts", lambda container_home="/root": [])
    monkeypatch.setattr(runtime, "_validate_mount_path_identity", lambda spec: None)
    monkeypatch.setattr(
        runtime,
        "_ensure_runtime_image_available",
        lambda spec: pytest.fail("unsafe mount overlap must fail before Docker work"),
    )

    with pytest.raises(runtime_module.RuntimeError, match="inside another writable bind mount"):
        runtime.start(server)


def _host_user_module_with_content_mount(home_source, content_source):
    """Return a host-user module with disjoint manager-local writable mounts."""

    module = _host_user_module(home_source)
    get_base_spec = module.get_container_spec

    def _container_spec(server):
        spec = get_base_spec(server)
        spec["mounts"] = [dict(mount) for mount in spec["mounts"]]
        spec["mounts"].insert(
            0,
            {
                "source": str(content_source),
                "target": "/srv/server",
                "mode": "rw",
            },
        )
        return spec

    module.get_container_spec = _container_spec
    return module


def test_container_runtime_rejects_home_nested_after_host_translation(
    monkeypatch, tmp_path
):
    _set_runtime_backend(monkeypatch, "docker")
    manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    content_source = manager_root / "content"
    server = DummyServer(
        module=_host_user_module_with_content_mount(home_source, content_source),
        data={"runtime": "docker"},
    )
    discovery_calls = []

    def _discover_mounts():
        discovery_calls.append(True)
        return [
            {"source": "/host/server", "destination": str(content_source)},
            {
                "source": "/host/server/runtime",
                "destination": str(manager_root / "runtime"),
            },
        ]

    runtime = runtime_module.ContainerRuntime()
    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_container_bind_mounts", _discover_mounts)
    monkeypatch.setattr(
        runtime,
        "_ensure_runtime_image_available",
        lambda spec: pytest.fail("translated overlap must fail before Docker work"),
    )

    with pytest.raises(
        runtime_module.RuntimeError,
        match="Host-visible container HOME source must not be inside another writable bind mount",
    ):
        runtime.start(server)

    assert discovery_calls == [True]
    assert not home_source.exists()


def test_host_user_runtime_rejects_symlinked_writable_source_before_manager_overlap(
    monkeypatch, tmp_path
):
    _set_runtime_backend(monkeypatch, "docker")
    manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    content_source = tmp_path / "content-link"
    content_source.symlink_to(manager_root, target_is_directory=True)
    server = DummyServer(
        module=_host_user_module_with_content_mount(home_source, content_source),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()
    monkeypatch.setattr(
        runtime,
        "_validate_mount_path_identity",
        lambda spec: pytest.fail(
            "symlinked writable source must fail before host translation"
        ),
    )

    with pytest.raises(
        runtime_module.RuntimeError,
        match="writable bind mount source must not contain symbolic links",
    ):
        runtime.start(server)

    assert not home_source.exists()


def test_translated_home_overlap_rejects_symlinked_writable_source(tmp_path):
    host_root = tmp_path / "host-state"
    home_source = host_root / "runtime" / "alpha" / "home"
    home_source.mkdir(parents=True)
    content_source = tmp_path / "host-content-link"
    content_source.symlink_to(host_root, target_is_directory=True)
    spec = {
        "container_home": "/home/alphagsm",
        "env": {"HOME": "/home/alphagsm"},
        "mounts": [
            {
                "source": str(content_source),
                "target": "/srv/server",
                "mode": "rw",
            },
            {
                "source": str(home_source),
                "target": "/home/alphagsm",
                "mode": "rw",
            },
        ],
    }

    with pytest.raises(
        runtime_module.RuntimeError,
        match="writable bind mount source must not contain symbolic links",
    ):
        runtime_module._validate_host_visible_host_user_home_overlap(spec)


def test_runtime_doctor_matches_start_before_docker_for_translated_home_overlap(
    monkeypatch, tmp_path
):
    _set_runtime_backend(monkeypatch, "docker")
    manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    content_source = manager_root / "content"
    server = DummyServer(
        module=_host_user_module_with_content_mount(home_source, content_source),
        data={"runtime": "docker"},
    )
    discovery_calls = []

    def _discover_mounts():
        discovery_calls.append(True)
        return [
            {"source": "/host/server", "destination": str(content_source)},
            {
                "source": "/host/server/runtime",
                "destination": str(manager_root / "runtime"),
            },
        ]

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_container_bind_mounts", _discover_mounts)

    def _unexpected_docker_health(*args, **kwargs):
        pytest.fail("translated overlap must fail before Docker health commands")

    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "docker_cli_version",
        _unexpected_docker_health,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "image_exists",
        _unexpected_docker_health,
    )
    monkeypatch.setattr(
        runtime_module.ContainerRuntime,
        "container_running_state",
        _unexpected_docker_health,
    )

    report = runtime_module.get_runtime_doctor_report(server)
    runtime = runtime_module.ContainerRuntime()
    monkeypatch.setattr(
        runtime,
        "_ensure_runtime_image_available",
        _unexpected_docker_health,
    )
    with pytest.raises(runtime_module.RuntimeError) as start_error:
        runtime.start(server)

    assert report["container_home_error"] == str(start_error.value)
    assert report["mount_path_identity_error"] == str(start_error.value)
    assert discovery_calls == [True, True]
    assert not home_source.exists()


def test_container_runtime_uses_disjoint_validated_host_translation_in_argv(
    monkeypatch, tmp_path
):
    _set_runtime_backend(monkeypatch, "docker")
    manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    content_source = manager_root / "content"
    server = DummyServer(
        module=_host_user_module_with_content_mount(home_source, content_source),
        data={"runtime": "docker"},
    )
    discovery_calls = []

    def _discover_mounts():
        discovery_calls.append(True)
        return [
            {"source": "/host/server", "destination": str(content_source)},
            {
                "source": "/host/state",
                "destination": str(manager_root / "runtime"),
            },
        ]

    runtime = runtime_module.ContainerRuntime()
    observed = []
    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_container_bind_mounts", _discover_mounts)
    monkeypatch.setattr(runtime, "_ensure_runtime_image_available", lambda spec: None)
    monkeypatch.setattr(runtime, "_container_running_state", lambda name: None)
    monkeypatch.setattr(
        runtime,
        "_run_check_output",
        lambda command, text=False: observed.append(command) or "ok",
    )

    runtime.start(server)

    assert discovery_calls == [True]
    assert "/host/server:/srv/server:rw" in observed[-1]
    assert "/host/state/alpha/home:/home/alphagsm:rw" in observed[-1]


@pytest.mark.parametrize("relative_source", (".", "manager"))
@pytest.mark.parametrize("inside_container", (False, True))
def test_host_user_runtime_rejects_relative_writable_sources_before_translation(
    monkeypatch, tmp_path, relative_source, inside_container
):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    module = _host_user_module(home_source)
    get_base_spec = module.get_container_spec

    def _container_spec(server):
        spec = get_base_spec(server)
        spec["mounts"].insert(
            0,
            {
                "source": relative_source,
                "target": "/srv/server",
                "mode": "rw",
            },
        )
        return spec

    module.get_container_spec = _container_spec
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(runtime_module.os, "getcwd", lambda: str(tmp_path))
    monkeypatch.setattr(
        runtime_module,
        "_running_inside_container",
        lambda: inside_container,
    )
    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [
            {
                "source": "/host/manager-root",
                "destination": str(tmp_path),
            }
        ]
        if inside_container
        else [],
    )
    monkeypatch.setattr(
        runtime,
        "_ensure_runtime_image_available",
        lambda spec: pytest.fail("relative writable source must fail before Docker work"),
    )

    with pytest.raises(
        runtime_module.RuntimeError,
        match="writable bind mount source must be absolute",
    ):
        runtime.start(server)


def test_container_runtime_rejects_spec_only_host_user_opt_in_as_mismatch(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "stdin_open": True,
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
            "env": {"HOME": "/home/alphagsm"},
            "mounts": [],
            "ports": [],
            "command": ["./TheFrontServer"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})

    monkeypatch.setattr(runtime_module.os, "geteuid", lambda: 0)
    monkeypatch.setattr(runtime_module.os, "getegid", lambda: 0)
    monkeypatch.setattr(
        runtime_module.sp,
        "check_output",
        lambda *args, **kwargs: pytest.fail("Docker must not run for a rejected root identity"),
    )

    with pytest.raises(
        runtime_module.RuntimeError,
        match="does not match authoritative runtime requirements",
    ):
        runtime_module.ContainerRuntime().start(server)


def test_container_runtime_rejects_root_requirement_before_container_spec(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    spec_calls = []

    def _unexpected_container_spec(_server):
        spec_calls.append(True)
        pytest.fail("container spec must not be resolved for a rejected root identity")

    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "steamcmd-linux",
            "run_as_host_user": True,
            "container_home": "/home/alphagsm",
        },
        get_container_spec=_unexpected_container_spec,
    )
    server = DummyServer(module=module, data={"runtime": "docker"})

    monkeypatch.setattr(runtime_module.os, "geteuid", lambda: 0)
    monkeypatch.setattr(runtime_module.os, "getegid", lambda: 0)
    monkeypatch.setattr(
        runtime_module.sp,
        "check_output",
        lambda *args, **kwargs: pytest.fail("Docker must not run for a rejected root identity"),
    )

    with pytest.raises(runtime_module.RuntimeError, match="effective UID is 0"):
        runtime_module.ContainerRuntime().start(server)

    assert spec_calls == []


def test_container_runtime_start_rejects_running_same_name_container(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": JAVA_RUNTIME_IMAGE,
            "runtime_family": "java",
            "working_dir": "/srv/server",
            "stdin_open": False,
            "env": {},
            "mounts": [],
            "ports": [],
            "command": ["java", "-jar", "server.jar"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        if cmd[:3] == ["docker", "image", "inspect"]:
            return "existing-image\n" if text else b"existing-image\n"
        if cmd[:3] == ["docker", "inspect", "-f"]:
            return "true\n" if text else b"true\n"
        raise AssertionError("docker run should not be attempted when the container is already running")

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    with pytest.raises(runtime_module.RuntimeError) as excinfo:
        runtime.start(server)

    assert "Docker container is already running: alphagsm-alpha" in str(excinfo.value)


def test_container_runtime_rejects_manager_container_only_mount_paths(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "stdin_open": True,
            "env": {},
            "mounts": [
                {"source": "/root/scp", "target": "/srv/server", "mode": "rw"},
            ],
            "ports": [],
            "command": ["./LocalAdmin", "7777"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(
        runtime_module,
        "_running_inside_container",
        lambda: True,
    )
    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [
            {
                "source": "/host/alphagsm",
                "destination": "/home/cosmosquark/sector_alpha/github/AlphaGSM/.alphagsm-docker",
            }
        ],
    )

    with pytest.raises(runtime_module.RuntimeError) as excinfo:
        runtime.start(server)

    assert "Path not visible to the host daemon: /root/scp" in str(excinfo.value)
    assert "ALPHAGSM_HOME" in str(excinfo.value)


def test_container_runtime_allows_mount_paths_under_manager_identity_root(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "stdin_open": False,
            "env": {},
            "mounts": [
                {
                    "source": "/home/cosmosquark/sector_alpha/github/AlphaGSM/.alphagsm-docker/servers/scp",
                    "target": "/srv/server",
                    "mode": "rw",
                },
            ],
            "ports": [],
            "command": ["./LocalAdmin", "7777"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return "existing-image\n" if text else b"existing-image\n"
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(
        runtime_module,
        "_running_inside_container",
        lambda: True,
    )
    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [
            {
                "source": "/host/alphagsm",
                "destination": "/home/cosmosquark/sector_alpha/github/AlphaGSM/.alphagsm-docker",
            }
        ],
    )
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.start(server)

    assert observed[-1][:3] == ["docker", "run", "-d"]


def test_build_container_spec_rejects_manager_container_only_paths_before_start_command(monkeypatch):
    server = DummyServer(data={"dir": "/root/scp/", "port": 7777})

    monkeypatch.setattr(
        runtime_module,
        "_running_inside_container",
        lambda: True,
    )
    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [
            {
                "source": "/host/alphagsm",
                "destination": "/home/cosmosquark/sector_alpha/github/AlphaGSM/.alphagsm-docker",
            }
        ],
    )

    def _unexpected_get_start_command(_server):
        raise AssertionError("get_start_command should not run for an invalid manager-only path")

    with pytest.raises(runtime_module.RuntimeError) as excinfo:
        runtime_module.build_container_spec(
            server,
            family="steamcmd-linux",
            get_start_command=_unexpected_get_start_command,
            port_definitions=(),
        )

    assert "Path not visible to the host daemon: /root/scp" in str(excinfo.value)


def test_default_install_dir_prefers_shared_servers_root_in_manager_mode(monkeypatch):
    server = DummyServer(name="scp")

    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", "/shared/alphagsm.conf")
    monkeypatch.setattr(
        runtime_module,
        "_current_container_identity_mount_roots",
        lambda: ["/shared"],
    )

    assert runtime_module.default_install_dir(server) == "/shared/servers/scp"


def test_current_container_identity_mount_roots_inspects_docker_without_tty_kwarg(monkeypatch):
    observed = {}

    def _fake_check_output(cmd, **kwargs):
        observed["cmd"] = cmd
        observed["kwargs"] = kwargs
        return '[{"Type":"bind","Source":"/shared","Destination":"/shared"}]'

    monkeypatch.setenv("HOSTNAME", "alphagsm-manager")
    monkeypatch.setattr(runtime_module.os.path, "exists", lambda path: path == "/.dockerenv")
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    roots = runtime_module._current_container_identity_mount_roots()

    assert roots == ["/shared"]
    assert observed["cmd"] == ["docker", "inspect", "-f", "{{json .Mounts}}", "alphagsm-manager"]
    assert observed["kwargs"] == {
        "stderr": runtime_module.sp.STDOUT,
        "shell": False,
        "text": True,
    }


def test_current_container_bind_mounts_exposes_source_destination_pairs(monkeypatch):
    observed = {}

    def _fake_check_output(cmd, **kwargs):
        observed["cmd"] = cmd
        observed["kwargs"] = kwargs
        return (
            '[{"Type":"bind","Source":"/home/runner/work","Destination":"/__w"},'
            '{"Type":"volume","Source":"ignored","Destination":"/data"},'
            '{"Type":"bind","Source":"/shared","Destination":"/shared"}]'
        )

    monkeypatch.setenv("HOSTNAME", "alphagsm-manager")
    monkeypatch.setattr(runtime_module.os.path, "exists", lambda path: path == "/.dockerenv")
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    mounts = runtime_module._current_container_bind_mounts()

    assert mounts == [
        {"source": "/home/runner/work", "destination": "/__w"},
        {"source": "/shared", "destination": "/shared"},
    ]
    assert observed["cmd"] == ["docker", "inspect", "-f", "{{json .Mounts}}", "alphagsm-manager"]
    assert observed["kwargs"] == {
        "stderr": runtime_module.sp.STDOUT,
        "shell": False,
        "text": True,
    }


def test_current_container_bind_mounts_uses_kernel_hostname_when_env_is_reset(
    monkeypatch,
):
    observed = {}

    def _fake_check_output(cmd, **kwargs):
        observed["cmd"] = cmd
        observed["kwargs"] = kwargs
        return (
            '[{"Type":"bind","Source":"/home/runner/work/_temp",'
            '"Destination":"/__w/_temp"}]'
        )

    monkeypatch.delenv("HOSTNAME", raising=False)
    monkeypatch.setattr(runtime_module.os.path, "exists", lambda path: path == "/.dockerenv")
    monkeypatch.setattr(
        runtime_module,
        "socket",
        SimpleNamespace(gethostname=lambda: "github-job-container"),
        raising=False,
    )
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    mounts = runtime_module._current_container_bind_mounts()

    assert mounts == [
        {
            "source": "/home/runner/work/_temp",
            "destination": "/__w/_temp",
        }
    ]
    assert observed["cmd"] == [
        "docker",
        "inspect",
        "-f",
        "{{json .Mounts}}",
        "github-job-container",
    ]


def test_translate_manager_container_path_to_host_uses_longest_bind_mount(monkeypatch):
    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [
            {"source": "/home/runner/work", "destination": "/__w"},
            {"source": "/home/runner/work/_temp", "destination": "/__w/_temp"},
        ],
    )

    translated = runtime_module._translate_manager_container_path_to_host(
        "/__w/_temp/alphagsm-work/server"
    )

    assert translated == "/home/runner/work/_temp/alphagsm-work/server"


def test_validate_mount_path_identity_allows_paths_under_non_identity_bind_mounts(monkeypatch):
    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [{"source": "/home/runner/work", "destination": "/__w"}],
    )

    runtime_module.validate_mount_path_identity(
        [{"source": "/__w/_temp/alphagsm-work/server", "target": "/srv/server", "mode": "rw"}]
    )


@pytest.mark.parametrize("discovery_result", ("inspect_failure", "empty_mounts"))
def test_validate_mount_path_identity_fails_closed_inside_container_without_mapping(
    monkeypatch, discovery_result
):
    monkeypatch.setenv("HOSTNAME", "alphagsm-manager")
    monkeypatch.setattr(
        runtime_module.os.path,
        "exists",
        lambda path: path == "/.dockerenv",
    )

    if discovery_result == "inspect_failure":
        monkeypatch.setattr(
            runtime_module.sp,
            "check_output",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("inspect unavailable")),
        )
    else:
        monkeypatch.setattr(runtime_module.sp, "check_output", lambda *args, **kwargs: "[]")

    with pytest.raises(
        runtime_module.RuntimeError,
        match="cannot establish a host-visible bind-mount mapping",
    ):
        runtime_module.validate_mount_path_identity(
            [{"source": "/srv/manager/server", "target": "/srv/server", "mode": "rw"}]
        )


def test_validate_mount_path_identity_preserves_bare_host_without_mount_mapping(monkeypatch):
    monkeypatch.setattr(runtime_module.os.path, "exists", lambda path: False)
    monkeypatch.setattr(
        runtime_module.sp,
        "check_output",
        lambda *args, **kwargs: pytest.fail("bare-host validation must not inspect itself"),
    )

    runtime_module.validate_mount_path_identity(
        [{"source": "/srv/host/server", "target": "/srv/server", "mode": "rw"}]
    )


def test_container_runtime_fails_closed_for_unmapped_manager_home(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    _manager_root, home_source = _set_manager_state_root(monkeypatch, tmp_path)
    _create_secure_runtime_home(home_source)
    server = DummyServer(
        module=_host_user_module(home_source),
        data={"runtime": "docker"},
    )
    runtime = runtime_module.ContainerRuntime()

    monkeypatch.setattr(
        runtime_module.os.path,
        "exists",
        lambda path: path == "/.dockerenv",
    )
    monkeypatch.setattr(runtime_module, "_current_container_bind_mounts", lambda: [])
    monkeypatch.setattr(runtime_module, "_current_container_identity_mount_roots", lambda: [])
    monkeypatch.setattr(
        runtime,
        "_ensure_runtime_image_available",
        lambda spec: pytest.fail("unmapped manager HOME must fail before Docker work"),
    )

    with pytest.raises(
        runtime_module.RuntimeError,
        match="cannot establish a host-visible bind-mount mapping",
    ) as excinfo:
        runtime.start(server)

    assert str(home_source) in str(excinfo.value)


def test_container_runtime_rewrites_manager_container_mount_sources_to_host_paths(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "stdin_open": False,
            "env": {},
            "mounts": [
                {
                    "source": "/__w/_temp/alphagsm-work/server",
                    "target": "/srv/server",
                    "mode": "rw",
                },
            ],
            "ports": [],
            "command": ["./LocalAdmin", "7777"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()

    observed = []

    def _fake_check_output(cmd, stderr=None, shell=False, text=False):
        observed.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return "existing-image\n" if text else b"existing-image\n"
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [{"source": "/home/runner/work", "destination": "/__w"}],
    )
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.start(server)

    assert observed[-1] == [
        "docker",
        "run",
        "-d",
        "--name",
        "alphagsm-alpha",
        "--network",
        "bridge",
        "-w",
        "/srv/server",
        "-v",
        "/home/runner/work/_temp/alphagsm-work/server:/srv/server:rw",
        STEAMCMD_RUNTIME_IMAGE,
        "./LocalAdmin",
        "7777",
    ]


def test_container_runtime_carries_single_discovered_mount_mapping_into_docker_argv(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "container_name": "alphagsm-alpha",
            "image": STEAMCMD_RUNTIME_IMAGE,
            "runtime_family": "steamcmd-linux",
            "working_dir": "/srv/server",
            "env": {},
            "mounts": [
                {
                    "source": "/__w/alphagsm/server",
                    "target": "/srv/server",
                    "mode": "rw",
                }
            ],
            "ports": [],
            "command": ["./server"],
        }
    )
    server = DummyServer(module=module, data={"runtime": "docker"})
    runtime = runtime_module.ContainerRuntime()
    discovery_calls = []
    observed = []

    def _discover_mounts():
        discovery_calls.append(True)
        if len(discovery_calls) == 1:
            return [{"source": "/host/work", "destination": "/__w"}]
        return []

    def _fake_check_output(command, stderr=None, shell=False, text=False):
        observed.append(command)
        if command[:3] == ["docker", "image", "inspect"]:
            return "existing-image\n" if text else b"existing-image\n"
        return "ok\n" if text else b"ok\n"

    monkeypatch.setattr(runtime_module.os.path, "exists", lambda path: path == "/.dockerenv")
    monkeypatch.setattr(runtime_module, "_current_container_bind_mounts", _discover_mounts)
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    runtime.start(server)

    assert discovery_calls == [True]
    assert "/host/work/alphagsm/server:/srv/server:rw" in observed[-1]
    assert "/__w/alphagsm/server:/srv/server:rw" not in observed[-1]


def test_default_install_dir_uses_home_on_normal_host(monkeypatch):
    server = DummyServer(name="scp")

    monkeypatch.delenv("ALPHAGSM_CONFIG_LOCATION", raising=False)
    monkeypatch.setattr(runtime_module, "_current_container_identity_mount_roots", lambda: [])
    monkeypatch.setattr(runtime_module.os.path, "expanduser", lambda path: path.replace("~", "/home/test"))

    assert runtime_module.default_install_dir(server) == "/home/test/scp"


def test_suggest_install_dir_keeps_existing_valid_path(monkeypatch):
    server = DummyServer(name="scp", data={"dir": "/srv/custom-scp"})

    monkeypatch.setattr(runtime_module, "_current_container_identity_mount_roots", lambda: [])

    assert runtime_module.suggest_install_dir(server) == "/srv/custom-scp"


def test_suggest_install_dir_replaces_stale_manager_only_path(monkeypatch):
    server = DummyServer(name="scp", data={"dir": "/root/scp"})

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(
        runtime_module,
        "_current_container_bind_mounts",
        lambda: [{"source": "/host/shared", "destination": "/shared"}],
    )
    monkeypatch.setattr(runtime_module, "default_install_dir", lambda current_server: "/shared/servers/" + current_server.name)

    assert runtime_module.suggest_install_dir(server) == "/shared/servers/scp"


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
                image=JAVA_RUNTIME_IMAGE,
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
    assert metadata["image"] == JAVA_RUNTIME_IMAGE


def test_ensure_runtime_hooks_adds_defaults_for_plain_module(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    monkeypatch.setattr(runtime_module, "_steamcmd_sdk_mounts", lambda: [])
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
    assert metadata["image"] == STEAMCMD_RUNTIME_IMAGE
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

    assert spec["working_dir"] == "/srv/server"
    assert spec["command"] == ["java", "-jar", "minecraft_server.jar"]
    assert spec["mounts"] == [
        {"source": str(server_root) + "/", "target": "/srv/server", "mode": "rw"},
        {"source": str(cache_root), "target": str(cache_root), "mode": "ro"},
    ]


def test_get_container_spec_rewrites_external_launcher_cwd_from_install_root(monkeypatch, tmp_path):
    _set_runtime_backend(monkeypatch, "docker")
    server_root = tmp_path / "server"
    cache_root = tmp_path / "downloads" / "cache"
    server_root.mkdir(parents=True)
    cache_root.mkdir(parents=True)
    target = cache_root / "DedicatedServerCmd"
    target.write_text("", encoding="utf-8")
    os.symlink(target, server_root / "DedicatedServerCmd")

    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "steamcmd-linux",
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
            "command": ["./DedicatedServerCmd"],
        },
    )
    server = DummyServer(
        module=module,
        data={"dir": str(server_root) + "/", "exe_name": "DedicatedServerCmd"},
    )

    spec = runtime_module.get_container_spec(server)

    assert spec["working_dir"] == str(cache_root)
    assert spec["mounts"] == [
        {"source": str(server_root) + "/", "target": "/srv/server", "mode": "rw"},
        {"source": str(cache_root), "target": str(cache_root), "mode": "ro"},
    ]
    assert spec["command"] == ["./DedicatedServerCmd"]


def test_get_container_spec_promotes_interactive_java_to_exec_console(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    module = SimpleNamespace(
        get_runtime_requirements=lambda server: {
            "engine": "docker",
            "family": "java",
            "java": 25,
        },
        get_container_spec=lambda server: {
            "working_dir": "/srv/server",
            "stdin_open": True,
            "tty": True,
            "env": {},
            "mounts": [],
            "ports": [],
            "command": ["java", "-jar", "minecraft_server.jar"],
        },
    )
    server = DummyServer(module=module, data={"dir": "/srv/server/"})

    spec = runtime_module.get_container_spec(server)

    assert spec["stop_mode"] == "exec-console"


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


def test_resolve_query_host_uses_bridge_gateway_inside_container(monkeypatch):
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

    observed = []

    def _fake_check_output(*args, **kwargs):
        observed.append(args[0])
        if "Gateway" in args[0][3]:
            return "172.17.0.1\n"
        return "172.17.0.4\n"

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    assert runtime_module.resolve_query_host(server) == "172.17.0.1"
    assert any("Gateway" in command[3] for command in observed)


def test_resolve_query_host_uses_container_ip_when_gateway_missing(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(data={"runtime": "docker", "container_name": "alphagsm-alpha"})

    def _fake_check_output(*args, **kwargs):
        if "Gateway" in args[0][3]:
            return "\n"
        return "172.18.0.7\n"

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    assert runtime_module.resolve_query_host(server) == "172.18.0.7"


def test_resolve_query_host_ignores_docker_no_value_gateway(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(data={"runtime": "docker", "container_name": "alphagsm-alpha"})

    def _fake_check_output(*args, **kwargs):
        if "Gateway" in args[0][3]:
            return "<no value>\n"
        return "172.18.0.7\n"

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    assert runtime_module.resolve_query_host(server) == "172.18.0.7"


def test_resolve_query_host_ignores_non_ip_docker_network_values(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(data={"runtime": "docker", "container_name": "alphagsm-alpha"})

    def _fake_check_output(*args, **kwargs):
        if "Gateway" in args[0][3]:
            return "map[]\n"
        return "172.18.0.7\n"

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    assert runtime_module.resolve_query_host(server) == "172.18.0.7"


def test_resolve_query_host_uses_default_on_host_for_docker_runtime(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(data={"runtime": "docker", "container_name": "alphagsm-alpha"})

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: False)

    assert runtime_module.resolve_query_host(server) == "127.0.0.1"


def test_resolve_query_host_prefers_explicit_public_ip(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(
        data={"runtime": "docker", "publicip": "192.168.1.50"},
    )

    assert runtime_module.resolve_query_host(server) == "192.168.1.50"


def test_resolve_query_host_ignores_explicit_docker_no_value(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = DummyServer(
        data={"runtime": "docker", "publicip": "<no value>", "container_name": "alphagsm-alpha"},
    )

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)

    def _fake_check_output(*args, **kwargs):
        if "Gateway" in args[0][3]:
            return "172.17.0.1\n"
        return "172.18.0.7\n"

    monkeypatch.setattr(runtime_module.sp, "check_output", _fake_check_output)

    assert runtime_module.resolve_query_host(server) == "172.17.0.1"


def test_resolve_query_host_falls_back_for_server_stubs_without_name(monkeypatch):
    _set_runtime_backend(monkeypatch, "docker")
    server = SimpleNamespace(data={"runtime": "docker", "container_name": "alphagsm-alpha"})

    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)

    assert runtime_module.resolve_query_host(server) == "127.0.0.1"


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
