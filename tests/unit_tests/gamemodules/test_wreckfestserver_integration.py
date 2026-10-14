"""Wreckfest CI backend selection and failed-start cleanup regressions."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def integration(monkeypatch):
    from tests.integration_tests import conftest as helpers

    monkeypatch.setitem(sys.modules, "conftest", helpers)
    path = Path(__file__).resolve().parents[2] / "integration_tests/test_wreckfestserver.py"
    spec = importlib.util.spec_from_file_location("wreckfest_integration_regression", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("backend", ["process", "docker"])
def test_baseline_honors_ci_selected_backend(integration, tmp_path, monkeypatch, backend):
    monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", backend)
    calls = []
    monkeypatch.setattr(integration, "_run_wreckfestserver_lifecycle",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    integration.test_wreckfestserver_lifecycle(tmp_path)
    assert calls == [((tmp_path,), {"runtime_backend": backend})]


def test_baseline_uses_shared_default_outside_ci(integration, tmp_path, monkeypatch):
    monkeypatch.delenv("ALPHAGSM_TEST_RUNTIME_BACKEND", raising=False)
    monkeypatch.setattr(integration, "default_runtime_backend", lambda: "process")
    calls = []
    monkeypatch.setattr(integration, "_run_wreckfestserver_lifecycle",
                        lambda *args, **kwargs: calls.append(kwargs))
    integration.test_wreckfestserver_lifecycle(tmp_path)
    assert calls == [{"runtime_backend": "process"}]


def test_opt_in_workshop_keeps_explicit_runtime_case(integration, tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
    calls = []
    monkeypatch.setattr(integration, "_run_wreckfestserver_lifecycle",
                        lambda *args, **kwargs: calls.append(kwargs))
    integration.test_wreckfestserver_native_workshop(tmp_path, "docker")
    assert calls == [{"runtime_backend": "docker", "workshop_fixture": True}]


@pytest.mark.parametrize("workshop_fixture", [False, True])
def test_cleanup_stops_baseline_and_cleans_only_opt_in_workshop(
        integration, monkeypatch, workshop_fixture):
    calls = []
    failure = RuntimeError("original readiness failure")
    result = SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(integration, "capture_alphagsm_stop",
                        lambda *args, **kwargs: calls.append(("stop", args[2])) or result)
    monkeypatch.setattr(integration, "run_alphagsm",
                        lambda *args: calls.append(tuple(args[1:])) or result)
    monkeypatch.setattr(integration, "log_command_result", lambda *_: None)
    integration._cleanup_wreckfest({}, "owned", workshop_fixture, failure)
    assert calls == [("stop", failure)] + ([("owned", "mod", "cleanup")] if workshop_fixture else [])


def test_failed_stop_does_not_clean_active_payloads_or_mask_original_failure(integration, monkeypatch):
    failed_stop = SimpleNamespace(returncode=1, stdout="", stderr="stop failed")
    monkeypatch.setattr(integration, "capture_alphagsm_stop", lambda *args, **kwargs: failed_stop)
    monkeypatch.setattr(integration, "run_alphagsm", lambda *_: pytest.fail("Cannot clean after failed stop"))
    integration._cleanup_wreckfest({}, "owned", True, RuntimeError("readiness failed"))
    with pytest.raises(AssertionError, match="stop failed"):
        integration._cleanup_wreckfest({}, "owned", True, None)


def test_workshop_cleanup_exception_does_not_replace_readiness_failure(integration, monkeypatch):
    result = SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(integration, "capture_alphagsm_stop", lambda *args, **kwargs: result)
    def failed_cleanup(*_):
        raise OSError("cleanup command failed")
    monkeypatch.setattr(integration, "run_alphagsm", failed_cleanup)
    integration._cleanup_wreckfest({}, "owned", True, RuntimeError("readiness failed"))
    with pytest.raises(OSError, match="cleanup command failed"):
        integration._cleanup_wreckfest({}, "owned", True, None)


def test_failed_start_is_inside_cleanup_scope(integration, tmp_path, monkeypatch):
    for name in ("ALPHAGSM_WRECKFESTSERVER_TEST_INSTALL", "ALPHAGSM_WRECKFESTSERVER_TEST_CACHE"):
        monkeypatch.delenv(name, raising=False)
    for name in ("require_integration_opt_in", "require_steamcmd_opt_in", "require_proton"):
        monkeypatch.setattr(integration, name, lambda: None)
    monkeypatch.setattr(integration, "require_command_for_runtime", lambda *args, **kwargs: None)
    monkeypatch.setattr(integration, "effective_runtime_backend", lambda backend, **_: backend)
    monkeypatch.setattr(integration, "write_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(integration, "alphagsm_env", lambda _: {})
    monkeypatch.setattr(integration, "resolve_runtime_image", lambda *_: pytest.fail("Process case must not resolve Docker image"))
    ports = iter((33540, 27016, 27015))
    monkeypatch.setattr(integration, "pick_free_udp_port", lambda: next(ports))
    result = SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(integration, "run_setup_with_port_retry", lambda *args, **kwargs: (result, args[2]))
    failed_start = RuntimeError("start command failed")
    def run_command(_env, _server, *command):
        if command == ("start",):
            raise failed_start
        return result
    monkeypatch.setattr(integration, "run_and_assert_ok", run_command)
    cleanups = []
    monkeypatch.setattr(integration, "_cleanup_wreckfest", lambda *args: cleanups.append(args))
    with pytest.raises(RuntimeError) as error:
        integration._run_wreckfestserver_lifecycle(tmp_path, runtime_backend="process")
    assert error.value is failed_start
    assert len(cleanups) == 1 and cleanups[0][2:] == (False, failed_start)


@pytest.mark.parametrize("settings,expected", [
    ({}, "process"),
    ({"GITHUB_ACTIONS": "true"}, "docker"),
    ({"ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON": "branch-image"}, "docker"),
    ({"ALPHAGSM_TEST_RUNTIME_BACKEND": "process", "GITHUB_ACTIONS": "true",
      "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON": "branch-image"}, "process"),
    ({"ALPHAGSM_TEST_RUNTIME_BACKEND": "docker"}, "docker"),
    ({"ALPHAGSM_TEST_RUNTIME_BACKEND": "auto"}, "docker"),
])
def test_smoke_runtime_selector_respects_ci_without_starting_servers(settings, expected):
    path = Path(__file__).resolve().parents[2] / "smoke_tests/run_wreckfestserver.sh"
    source = path.read_text(encoding="utf-8")
    selector = source[source.index('RUNTIME_BACKEND="'):source.index('LOCAL_WINE_PROTON_IMAGE="')]
    environment = os.environ.copy()
    environment.pop("BASH_ENV", None)
    for key in ("ALPHAGSM_TEST_RUNTIME_BACKEND", "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON", "GITHUB_ACTIONS"):
        environment.pop(key, None)
    environment.update(settings)
    result = subprocess.run(["bash", "-c", selector + '\nprintf "%s" "$RUNTIME_BACKEND"'],
                            env=environment, text=True, capture_output=True, check=True)
    assert result.stdout == expected
