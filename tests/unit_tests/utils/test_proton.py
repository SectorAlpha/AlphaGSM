"""Unit tests for utils.proton – Wine/Proton wrapping helpers."""

import os
import shlex
import types

import pytest

import utils.proton as proton_module


def test_console_wrapper_quotes_arguments_without_executing_them():
    command = ["env", "VALUE=space and $(literal)", "/path with spaces/wine", "cmd.exe", "/c", "server.exe"]
    wrapped = proton_module.wrap_console_command(command)
    assert wrapped[:2] == ["script", "-qefc"]
    assert wrapped[-1] == "/dev/null"
    assert shlex.split(wrapped[2]) == command


@pytest.mark.parametrize("prefer_proton", [False, True])
def test_xvfb_wrap_preserves_runtime_prefix_and_exposes_x11_driver(tmp_path, monkeypatch, prefer_proton):
    monkeypatch.setattr(proton_module, 'find_wine', lambda: '/usr/bin/wine')
    monkeypatch.setattr(proton_module, 'find_proton', lambda: '/opt/proton/proton')
    native = ['server.exe', '-noconsole', 'WINEDLLOVERRIDES=native-argument']
    prefix = str(tmp_path / 'private-prefix')
    command = proton_module.wrap_xvfb_command(native, wineprefix=prefix, prefer_proton=prefer_proton)
    assert command[:2] == ['xvfb-run', '-a']
    assert 'WINEDLLOVERRIDES=winex11.drv=' not in command and 'DISPLAY=' not in command
    assert 'WINEDLLOVERRIDES=' in command and 'SDL_VIDEODRIVER=x11' in command
    assert ('STEAM_COMPAT_DATA_PATH=' if prefer_proton else 'WINEPREFIX=') + prefix in command
    assert ('/opt/proton/proton' if prefer_proton else '/usr/bin/wine') in command
    assert proton_module.unwrap_runtime_command(command) == native


def test_prepare_wineprefix_copies_runtime_template_into_fresh_prefix(tmp_path):
    template = tmp_path / "prepared"
    template.mkdir()
    (template / "system.reg").write_text("installed C++ runtime")
    (template / "drive_c/windows/system32").mkdir(parents=True)
    (template / "drive_c/windows/system32/vcruntime140.dll").write_bytes(b"native runtime")
    prefix = tmp_path / "server/prefix"
    assert proton_module.prepare_wineprefix(prefix, template=template)
    assert (prefix / "system.reg").read_text() == "installed C++ runtime"
    assert (prefix / "drive_c/windows/system32/vcruntime140.dll").read_bytes() == b"native runtime"


@pytest.mark.parametrize("timestamp", ["1712345678\n", "disable\n"])
def test_prepare_wineprefix_reinitializes_copied_user_profile(tmp_path, timestamp):
    template, prefix = tmp_path / "root-template", tmp_path / "private-prefix"
    template.mkdir()
    (template / "system.reg").write_text("installed native runtime")
    (template / ".update-timestamp").write_text(timestamp)
    (template / "user.reg").write_text("prepared application settings")

    assert proton_module.prepare_wineprefix(prefix, template=template)

    # Wine must run its normal profile/shell-folder setup for the receiving
    # account instead of trusting the image builder's completed update.
    assert not (prefix / ".update-timestamp").exists()
    assert (template / ".update-timestamp").read_text() == timestamp
    assert (prefix / "user.reg").read_text() == "prepared application settings"


def test_prepare_wineprefix_preserves_existing_update_timestamp(tmp_path):
    template, prefix = tmp_path / "template", tmp_path / "operator-prefix"
    template.mkdir()
    (template / "system.reg").write_text("template runtime")
    prefix.mkdir()
    (prefix / ".update-timestamp").write_text("disable\n")

    assert not proton_module.prepare_wineprefix(prefix, template=template)
    assert (prefix / ".update-timestamp").read_text() == "disable\n"
    assert not (prefix / "system.reg").exists()


@pytest.mark.parametrize("existing", ["system.reg", "operator.txt", "pfx/system.reg"])
def test_prepare_wineprefix_preserves_existing_wine_or_proton_prefix(tmp_path, existing):
    template, prefix = tmp_path / "prepared", tmp_path / "prefix"
    template.mkdir()
    (template / "system.reg").write_text("template")
    target = prefix / existing
    target.parent.mkdir(parents=True)
    target.write_text("operator")
    assert not proton_module.prepare_wineprefix(prefix, template=template)
    assert target.read_text() == "operator"
    assert sorted(path.relative_to(prefix).as_posix() for path in prefix.rglob("*") if path.is_file()) == [existing]


def test_prepare_wineprefix_without_template_does_not_create_empty_prefix(tmp_path):
    prefix = tmp_path / "new-prefix"
    assert not proton_module.prepare_wineprefix(prefix, template=tmp_path / "missing")
    assert not prefix.exists()


class DummyServer:
    def __init__(self, name="alpha", data=None):
        self.name = name
        self.data = {} if data is None else data


# ---------------------------------------------------------------------------
# find_wine
# ---------------------------------------------------------------------------

def test_find_wine_returns_none_when_not_found(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    assert proton_module.find_wine() is None


def test_find_wine_returns_path_when_present(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    assert proton_module.find_wine() == "/usr/bin/wine"


# ---------------------------------------------------------------------------
# find_proton
# ---------------------------------------------------------------------------

def test_find_proton_returns_none_when_no_search_dirs_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "nonexistent")])
    assert proton_module.find_proton() is None


def test_find_proton_returns_proton_script_when_found(tmp_path, monkeypatch):
    # Simulate GE-Proton9-27/proton inside a search dir
    tool_dir = tmp_path / "compat" / "GE-Proton9-27"
    tool_dir.mkdir(parents=True)
    proton_exe = tool_dir / "proton"
    proton_exe.write_text("#!/bin/bash\n")

    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])
    assert proton_module.find_proton() == str(proton_exe)


def test_find_proton_returns_latest_version(tmp_path, monkeypatch):
    """When multiple tool dirs exist, the lexicographically last is preferred."""
    compat = tmp_path / "compat"
    for name in ("GE-Proton8-10", "GE-Proton9-27"):
        d = compat / name
        d.mkdir(parents=True)
        (d / "proton").write_text("#!/bin/bash\n")

    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(compat)])
    result = proton_module.find_proton()
    assert "GE-Proton9-27" in result


def test_find_proton_skips_non_directory_entries(tmp_path, monkeypatch):
    """Loose files in the search dir are ignored; only subdirs with proton count."""
    compat = tmp_path / "compat"
    compat.mkdir()
    (compat / "not-a-dir.tar.gz").write_text("")  # a file, not a dir

    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(compat)])
    assert proton_module.find_proton() is None


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

def test_is_available_false_when_neither(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [])
    assert proton_module.is_available() is False


def test_is_available_true_when_wine_present(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    assert proton_module.is_available() is True


def test_is_available_true_when_proton_found(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    tool_dir = tmp_path / "compat" / "GE-Proton9-01"
    tool_dir.mkdir(parents=True)
    (tool_dir / "proton").write_text("#!/bin/bash\n")
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])
    assert proton_module.is_available() is True


# ---------------------------------------------------------------------------
# wrap_command – Wine paths
# ---------------------------------------------------------------------------

def test_wrap_command_with_wine_no_prefix(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    result = proton_module.wrap_command(["server.exe"])
    assert result == [
        "env",
        "-u", "TMPDIR",
        "-u", "TMP",
        "-u", "TEMP",
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
        "/usr/bin/wine",
        "server.exe",
    ]


def test_wrap_command_with_wine_and_prefix(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    result = proton_module.wrap_command(["server.exe"], wineprefix="/srv/game/.wine")
    assert result == [
        "env",
        "-u", "TMPDIR",
        "-u", "TMP",
        "-u", "TEMP",
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
        "WINEPREFIX=/srv/game/.wine",
        "/usr/bin/wine",
        "server.exe",
    ]


def test_wrap_command_prefers_proton_when_requested(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    tool_dir = tmp_path / "compat" / "GE-Proton9-27"
    tool_dir.mkdir(parents=True)
    proton_exe = tool_dir / "proton"
    proton_exe.write_text("#!/bin/bash\n")
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])

    result = proton_module.wrap_command(["server.exe"], prefer_proton=True)

    assert result[0] == "env"
    assert str(proton_exe) in result
    assert "run" in result
    assert "/usr/bin/wine" not in result
    assert "PROTON_USE_XALIA=0" in result


def test_wrap_command_preserves_trailing_args(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    result = proton_module.wrap_command(["server.exe", "--port", "7000"])
    assert result == [
        "env",
        "-u", "TMPDIR",
        "-u", "TMP",
        "-u", "TEMP",
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
        "/usr/bin/wine",
        "server.exe",
        "--port",
        "7000",
    ]


def test_prepend_env_assignments_wraps_plain_command():
    result = proton_module.prepend_env_assignments(["server.exe"], LIBGL_ALWAYS_SOFTWARE="1")
    assert result == ["env", "LIBGL_ALWAYS_SOFTWARE=1", "server.exe"]


def test_prepend_env_assignments_inserts_before_existing_env_tokens():
    result = proton_module.prepend_env_assignments(
        ["env", "DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=", "/usr/bin/wine", "server.exe"],
        LIBGL_ALWAYS_SOFTWARE="1",
    )
    assert result == [
        "env",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
        "/usr/bin/wine",
        "server.exe",
    ]


def test_prepend_env_assignments_preserves_existing_env_unsets():
    result = proton_module.prepend_env_assignments(
        [
            "env",
            "-u", "TMPDIR",
            "-u", "TMP",
            "-u", "TEMP",
            "DISPLAY=",
            "/usr/bin/wine",
            "server.exe",
        ],
        LIBGL_ALWAYS_SOFTWARE="1",
    )
    assert result == [
        "env",
        "-u", "TMPDIR",
        "-u", "TMP",
        "-u", "TEMP",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "DISPLAY=",
        "/usr/bin/wine",
        "server.exe",
    ]


def test_prepend_env_unsets_wraps_plain_command():
    result = proton_module.prepend_env_unsets(["server.exe"], "TMPDIR", "TMP")
    assert result == ["env", "-u", "TMPDIR", "-u", "TMP", "server.exe"]


def test_prepend_env_unsets_inserts_before_existing_env_tokens():
    result = proton_module.prepend_env_unsets(
        ["env", "DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=", "/usr/bin/wine", "server.exe"],
        "TMPDIR",
        "TMP",
        "TEMP",
    )
    assert result == [
        "env",
        "-u", "TMPDIR",
        "-u", "TMP",
        "-u", "TEMP",
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
        "/usr/bin/wine",
        "server.exe",
    ]


# ---------------------------------------------------------------------------
# wrap_command – Proton paths (wine absent)
# ---------------------------------------------------------------------------

def test_wrap_command_uses_proton_when_wine_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    tool_dir = tmp_path / "compat" / "GE-Proton9-27"
    tool_dir.mkdir(parents=True)
    proton_exe = tool_dir / "proton"
    proton_exe.write_text("#!/bin/bash\n")
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])
    monkeypatch.setattr(proton_module.os.path, "expanduser", lambda p: str(tmp_path / ".proton"))

    result = proton_module.wrap_command(["server.exe"])
    assert result[0] == "env"
    assert any("STEAM_COMPAT_DATA_PATH=" in tok for tok in result)
    assert str(proton_exe) in result
    assert "run" in result
    assert "server.exe" in result


def test_wrap_command_uses_wineprefix_for_proton_compat_path(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    tool_dir = tmp_path / "compat" / "GE-Proton9-27"
    tool_dir.mkdir(parents=True)
    proton_exe = tool_dir / "proton"
    proton_exe.write_text("#!/bin/bash\n")
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])

    custom_prefix = str(tmp_path / "myprefix")
    result = proton_module.wrap_command(["server.exe"], wineprefix=custom_prefix)
    assert f"STEAM_COMPAT_DATA_PATH={custom_prefix}" in result


# ---------------------------------------------------------------------------
# wrap_command – error when nothing available
# ---------------------------------------------------------------------------

def test_wrap_command_raises_when_unavailable(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [])
    with pytest.raises(RuntimeError, match="[Ww]ine"):
        proton_module.wrap_command(["server.exe"])


def test_unwrap_runtime_command_removes_wine_wrapper():
    command = [
        "env",
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
        "WINEPREFIX=/srv/game/.wine",
        "/usr/bin/wine",
        "Server.exe",
        "-port",
        "27015",
    ]

    result = proton_module.unwrap_runtime_command(command)

    assert result == ["Server.exe", "-port", "27015"]


def test_unwrap_runtime_command_skips_env_unset_options():
    command = [
        "env",
        "-u",
        "TMPDIR",
        "-u",
        "TMP",
        "DISPLAY=",
        "WINEDLLOVERRIDES=winex11.drv=",
        "/usr/bin/wine",
        "Server.exe",
        "-port",
        "27015",
    ]

    result = proton_module.unwrap_runtime_command(command)

    assert result == ["Server.exe", "-port", "27015"]


def test_unwrap_runtime_command_removes_env_wrapper_for_native_command():
    command = [
        "env",
        "SDL_VIDEODRIVER=x11",
        "SDL_AUDIODRIVER=dummy",
        "bin/Server.exe",
        "exec",
        "default.cfg",
    ]

    assert proton_module.unwrap_runtime_command(command) == [
        "bin/Server.exe",
        "exec",
        "default.cfg",
    ]


def test_unwrap_runtime_command_removes_xvfb_wrapper():
    command = [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        "env",
        "DISPLAY=",
        "/usr/bin/proton",
        "run",
        "Server.exe",
        "-port",
        "27015",
    ]

    assert proton_module.unwrap_runtime_command(command) == [
        "Server.exe",
        "-port",
        "27015",
    ]


def test_get_runtime_requirements_for_docker_mounts_prefix_and_ports():
    server = DummyServer(
        data={
            "dir": "/srv/aska/",
            "wineprefix": "/var/lib/alphagsm/aska-prefix",
            "port": 27015,
            "queryport": 27016,
        }
    )

    requirements = proton_module.get_runtime_requirements(
        server,
        port_definitions=(("port", "udp"), ("queryport", "udp")),
        prefer_proton=True,
        stop_mode="exec-console",
        stdin_open=True,
    )

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "wine-proton"
    assert requirements["mounts"] == [
        {"source": "/srv/aska/", "target": "/srv/server", "mode": "rw"},
        {
            "source": "/var/lib/alphagsm/aska-prefix",
            "target": "/srv/wineprefix",
            "mode": "rw",
        },
    ]
    assert requirements["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27016, "container": 27016, "protocol": "udp"},
    ]
    assert requirements["env"]["ALPHAGSM_WINEPREFIX"] == "/srv/wineprefix"
    assert requirements["env"]["ALPHAGSM_PREFER_PROTON"] == "1"
    assert requirements["env"]["PROTON_USE_XALIA"] == "0"
    assert requirements["stop_mode"] == "exec-console"
    assert requirements["stdin_open"] is True
    assert requirements["host_dependencies"][0]["id"] == "wine-proton"
    assert requirements["host_dependencies"][0]["platforms"] == ("linux",)


def test_get_runtime_requirements_appends_extra_host_dependencies():
    server = DummyServer(
        data={
            "dir": "/srv/aska/",
            "port": 27015,
        }
    )

    requirements = proton_module.get_runtime_requirements(
        server,
        port_definitions=(("port", "udp"),),
        extra_host_dependencies=(proton_module.xvfb_host_dependency(),),
    )

    dependency_ids = [item["id"] for item in requirements["host_dependencies"]]

    assert dependency_ids == ["wine-proton", "xvfb-run"]
    assert requirements["host_dependencies"][1]["platforms"] == ("linux",)


def test_get_container_spec_uses_unwrapped_command_and_runtime_env():
    server = DummyServer(
        data={
            "dir": "/srv/opz/",
            "port": 7777,
        }
    )

    spec = proton_module.get_container_spec(
        server,
        lambda _server: (
            [
                "env",
                "DISPLAY=",
                "WINEDLLOVERRIDES=winex11.drv=",
                "/usr/bin/wine",
                "WindowsServer/SurvivalGameServer.exe",
                "-Port=7777",
            ],
            "/srv/opz/",
        ),
        port_definitions=(("port", "udp"),),
    )

    assert spec["working_dir"] == "/srv/server"
    assert spec["command"] == ["./WindowsServer/SurvivalGameServer.exe", "-Port=7777"]
    assert spec["env"]["ALPHAGSM_WINEPREFIX"] == "/srv/server/.alphagsm-wineprefix"
    assert spec["mounts"] == [
        {"source": "/srv/opz/", "target": "/srv/server", "mode": "rw"}
    ]


@pytest.mark.parametrize("launcher", ["cmd.exe", "CMD.EXE"])
def test_container_spec_preserves_windows_command_processor_lookup(launcher):
    """A Windows system launcher must not become a nonexistent server-local file."""
    server = DummyServer(data={"dir": "/srv/wreckfest"})
    spec = proton_module.get_container_spec(
        server,
        lambda _server: (["env", "WINEDEBUG=-all", "/usr/bin/wine", launcher,
                          "/c", "Wreckfest_x64.exe", "-s"], "/srv/wreckfest"),
    )
    assert spec["command"] == [launcher, "/c", "Wreckfest_x64.exe", "-s"]
    assert spec["working_dir"] == "/srv/server"


@pytest.mark.parametrize(
    "data, expected_ports",
    [
        ({}, [{"host": 27020, "container": 27020, "protocol": "tcp"}]),
        ({"rconport": 28020}, [{"host": 28020, "container": 28020, "protocol": "tcp"}]),
        ({"rconport": None}, []),
    ],
)
def test_proton_port_definition_default_only_applies_when_key_is_absent(data, expected_ports):
    server = DummyServer(data=data)

    requirements = proton_module.get_runtime_requirements(
        server,
        port_definitions=({"key": "rconport", "default": 27020, "protocol": "tcp"},),
    )

    assert requirements.get("ports", []) == expected_ports
    assert server.data == data


def test_get_container_spec_recovers_when_host_runtime_wrapper_is_unavailable():
    server = DummyServer(
        data={
            "dir": "/srv/asa/",
            "wineprefix": "/srv/asa/.wine",
            "port": 7777,
        }
    )

    observed = []

    def fake_get_start_command(_server):
        observed.append("called")
        return (
            [
                proton_module.wrap_command(
                    ["WindowsServer/Server.exe", "-Port=7777"],
                    wineprefix=_server.data.get("wineprefix"),
                )
            ][0],
            "/srv/asa/",
        )

    proton_error = RuntimeError(
        "Neither Wine nor Proton-GE is available on this system.  Run  scripts/install_proton.sh  to install one of them."
    )

    original_wrap_command = proton_module.wrap_command

    def fake_wrap_command(command, **kwargs):
        if len(observed) == 1:
            raise proton_error
        return original_wrap_command(command, **kwargs)

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(proton_module, "wrap_command", fake_wrap_command)
        spec = proton_module.get_container_spec(
            server,
            fake_get_start_command,
            port_definitions=(("port", "udp"),),
        )
    finally:
        monkeypatch.undo()

    assert observed == ["called", "called"]
    assert spec["command"] == ["./WindowsServer/Server.exe", "-Port=7777"]
