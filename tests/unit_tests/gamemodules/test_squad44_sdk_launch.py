"""Squad 44 must select its installed SDK without leaking host paths to Docker."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

import gamemodules.squad44server as module


def _server(tmp_path, *, sdk=True):
    root = tmp_path / "installed server with spaces"
    root.mkdir()
    (root / "PostScriptumServer.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    if sdk:
        (root / "linux64").mkdir()
        (root / "linux64/steamclient.so").write_bytes(b"vendor sdk fixture")
    return SimpleNamespace(data={"dir": str(root), "exe_name": "PostScriptumServer.sh",
                                 "port": 7787, "queryport": 7788, "beaconport": 7797,
                                 "fixedmaxplayers": "80"})


def test_process_prefers_vendor_sdk_preserving_existing_library_path(tmp_path, monkeypatch):
    server = _server(tmp_path)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/operator/custom libs:/another/path")
    home = tmp_path / "operator home"
    (home / ".steam/sdk64").mkdir(parents=True)
    existing_sdk = home / ".steam/sdk64/steamclient.so"
    existing_sdk.write_bytes(b"operator SDK must remain untouched")
    monkeypatch.setenv("HOME", str(home))
    previous = deepcopy(server.data)
    command, cwd = module.get_start_command(server)
    assert command[:3] == ["env", "LD_LIBRARY_PATH=" + server.data["dir"]
                           + "/linux64:/operator/custom libs:/another/path",
                           "./PostScriptumServer.sh"]
    assert cwd == server.data["dir"]
    assert server.data == previous
    assert existing_sdk.read_bytes() == b"operator SDK must remain untouched"


def test_process_library_path_without_operator_value_has_no_empty_search_entry(tmp_path, monkeypatch):
    server = _server(tmp_path)
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    command, _ = module.get_start_command(server)
    assert command[1] == "LD_LIBRARY_PATH=" + server.data["dir"] + "/linux64"


@pytest.mark.parametrize("sdk", [False, True])
def test_container_uses_native_command_and_only_container_sdk_path(tmp_path, monkeypatch, sdk):
    server = _server(tmp_path, sdk=sdk)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/manager/private libs")
    captured = {}

    def build_spec(current_server, **kwargs):
        captured.update(kwargs)
        command, cwd = kwargs["get_start_command"](current_server)
        return {"command": command, "env": kwargs["env"], "working_dir": cwd}

    monkeypatch.setattr(module.runtime_module, "build_container_spec", build_spec)
    spec = module.get_container_spec(server)
    assert spec["command"][0] == "./PostScriptumServer.sh"
    assert spec["env"] == ({"LD_LIBRARY_PATH": "/srv/server/linux64"} if sdk else {})
    assert "/manager/private libs" not in repr(spec)
    assert captured["extra"]["run_as_host_user"] is True
    assert captured["extra"]["container_home"] == "/home/alphagsm"


def test_missing_vendor_sdk_keeps_existing_process_launcher(tmp_path, monkeypatch):
    server = _server(tmp_path, sdk=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/operator/lib")
    command, _ = module.get_start_command(server)
    assert command[0] == "./PostScriptumServer.sh"
    assert all(not part.startswith("LD_LIBRARY_PATH=") for part in command)


@pytest.mark.parametrize("sdk", [False, True])
def test_runtime_requirements_declare_same_container_sdk_selection(tmp_path, monkeypatch, sdk):
    server = _server(tmp_path, sdk=sdk)
    monkeypatch.setattr(module.runtime_module, "build_runtime_requirements",
                        lambda _server, **kwargs: kwargs)
    requirements = module.get_runtime_requirements(server)
    assert requirements["env"] == ({"LD_LIBRARY_PATH": "/srv/server/linux64"} if sdk else {})
