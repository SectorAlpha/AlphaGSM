"""Required anonymous Workshop CI cases cannot silently opt out or skip."""

import os
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import run_ci_workshop_tests as runner
from tests.integration_tests import workshop_ci_plugin as plugin


@pytest.mark.parametrize("exit_code", [0, 1, 42])
def test_runner_forces_workshop_flags_and_preserves_command_context(monkeypatch, exit_code):
    for flag in runner.WORKSHOP_FLAGS:
        monkeypatch.setenv(flag, "0")
    monkeypatch.setenv("ALPHAGSM_CI_WORKSHOP", "0")
    monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", "/owned/config")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-ra --strict-markers")
    invoke = Mock(return_value=SimpleNamespace(returncode=exit_code))
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    command = ["python3", "-m", "pytest", "a test.py", "--timeout=900"]

    assert runner.main(command) == exit_code

    invoke.assert_called_once()
    arguments, options = invoke.call_args
    assert arguments == (command,)
    assert options["check"] is False
    assert set(options) == {"env", "check"}, "Inherit working directory and stdio"
    environment = options["env"]
    assert all(environment[flag] == "1" for flag in runner.WORKSHOP_FLAGS)
    assert environment["ALPHAGSM_CI_WORKSHOP"] == "1"
    assert environment["ALPHAGSM_TEST_RUNTIME_BACKEND"] == "process"
    assert environment["ALPHAGSM_CONFIG_LOCATION"] == "/owned/config"
    assert environment["PYTEST_ADDOPTS"] == (
        "-ra --strict-markers -p tests.integration_tests.workshop_ci_plugin")
    assert os.environ["ALPHAGSM_CI_WORKSHOP"] == "0", "Do not mutate the caller's environment"


def test_runner_requires_a_command_without_starting_anything(monkeypatch, capsys):
    invoke = Mock()
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    assert runner.main([]) == 2
    invoke.assert_not_called()
    assert "Usage:" in capsys.readouterr().err


@pytest.mark.parametrize("prefix,kind,identifier", [
    ("ASRD", "ITEM", "848331447"), ("BB2", "ITEM", "710060895"),
    ("DOI", "ITEM", "823752012"), ("GMOD", "COLLECTION", "2886432224"),
    ("INS", "ITEM", "498253639"), ("NMRIH", "ITEM", "3514998402"),
    ("NS2", "ITEM", "129599221"), ("TF2", "ITEM", "454299390"),
])
def test_required_smoke_selects_public_fixture_without_changing_caller(
        monkeypatch, prefix, kind, identifier):
    for key in ("ITEM", "COLLECTION"):
        monkeypatch.delenv(f"{prefix}_WORKSHOP_{key}", raising=False)
    invoke = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    assert runner.main(["bash", str(runner.REPO_ROOT / "tests/smoke_tests/run_ns2server.sh")]) == 0
    assert invoke.call_args.kwargs["env"][f"{prefix}_WORKSHOP_{kind}"] == identifier
    assert f"{prefix}_WORKSHOP_{kind}" not in os.environ


@pytest.mark.parametrize("prefix", ["ASRD", "BB2", "DOI", "GMOD", "INS", "NMRIH", "NS2", "TF2"])
@pytest.mark.parametrize("kind", ["ITEM", "COLLECTION"])
def test_required_smoke_preserves_explicit_fixture_and_does_not_add_default(
        monkeypatch, prefix, kind):
    other = "ITEM" if kind == "COLLECTION" else "COLLECTION"
    monkeypatch.setenv(f"{prefix}_WORKSHOP_{kind}", "https://steamcommunity.com/sharedfiles/filedetails/?id=123")
    monkeypatch.delenv(f"{prefix}_WORKSHOP_{other}", raising=False)
    invoke = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    assert runner.main(["bash", str(runner.REPO_ROOT / "tests/smoke_tests/run_tf2.sh")]) == 0
    environment = invoke.call_args.kwargs["env"]
    assert environment[f"{prefix}_WORKSHOP_{kind}"] == os.environ[f"{prefix}_WORKSHOP_{kind}"]
    assert f"{prefix}_WORKSHOP_{other}" not in environment


def test_non_smoke_command_does_not_inherit_smoke_fixtures(monkeypatch):
    for key in ("ITEM", "COLLECTION"):
        monkeypatch.delenv(f"NS2_WORKSHOP_{key}", raising=False)
    invoke = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    assert runner.main(["python3", "-m", "pytest", "tests/integration_tests/test_ns2server.py"]) == 0
    assert "NS2_WORKSHOP_ITEM" not in invoke.call_args.kwargs["env"]


def test_runner_preserves_signal_exit_and_handles_unavailable_command(monkeypatch, capsys):
    monkeypatch.setattr(runner.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=-15)))
    assert runner.main(["owned-command"]) == 143
    monkeypatch.setattr(runner.subprocess, "run", Mock(side_effect=FileNotFoundError()))
    assert runner.main(["missing-command"]) == 127
    assert "Unable to execute CI Workshop command" in capsys.readouterr().err


@pytest.mark.parametrize("relative", sorted(runner.WORKSHOP_TEST_FILES))
def test_required_workshop_smoke_prerequisite_skip_is_a_failure(monkeypatch, capsys, relative):
    script = relative.replace("tests/integration_tests/test_", "tests/smoke_tests/run_").replace(".py", ".sh")
    monkeypatch.chdir(runner.REPO_ROOT)
    monkeypatch.setattr(runner.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=77)))
    assert runner.main(["bash", "./" + script]) == 1
    assert "Required anonymous Workshop smoke skipped" in capsys.readouterr().err


def test_required_workshop_smoke_absolute_direct_command_cannot_skip(monkeypatch):
    command = str(runner.REPO_ROOT / "tests/smoke_tests/run_squad44server.sh")
    monkeypatch.setattr(runner.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=77)))
    assert runner.main([command]) == 1


@pytest.mark.parametrize("command", [
    ["bash", "./tests/smoke_tests/run_dayzserver.sh"],
    ["bash", "./tests/smoke_tests/run_foundryserver.sh"],
    ["python3", "-m", "pytest", "tests/integration_tests/test_authenticated_server.py"],
    ["unrelated-command"],
])
def test_unrelated_auth_byo_or_non_smoke_skip_status_is_preserved(monkeypatch, command):
    monkeypatch.chdir(runner.REPO_ROOT)
    monkeypatch.setattr(runner.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=77)))
    assert runner.main(command) == 77


def test_same_named_script_outside_repository_does_not_become_required(monkeypatch, tmp_path):
    monkeypatch.setattr(runner.subprocess, "run", Mock(return_value=SimpleNamespace(returncode=77)))
    assert runner.main(["bash", str(tmp_path / "tests/smoke_tests/run_ark.sh")]) == 77


def test_registry_covers_every_checked_in_workshop_opt_in_gate():
    integration_dir = runner.REPO_ROOT / "tests/integration_tests"
    discovered_flags = set()
    for path in integration_dir.glob("test_*.py"):
        flags = set(re.findall(r"ALPHAGSM_RUN_(?:[A-Z0-9_]+_)?WORKSHOP", path.read_text()))
        if flags:
            assert path.relative_to(runner.REPO_ROOT).as_posix() in runner.WORKSHOP_TEST_FILES, path
            discovered_flags.update(flags)
    assert discovered_flags == set(runner.WORKSHOP_FLAGS)
    assert len(discovered_flags) == 12
    assert {"tests/integration_tests/test_conanexiles.py", "tests/integration_tests/test_squadserver.py"} <= (
        runner.WORKSHOP_TEST_FILES)


def _finish_report_hook(item, report):
    hook = plugin.pytest_runtest_makereport(item, None)
    next(hook)
    with pytest.raises(StopIteration):
        hook.send(SimpleNamespace(get_result=lambda: report))


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
@pytest.mark.parametrize("relative", sorted(runner.WORKSHOP_TEST_FILES))
def test_required_workshop_skip_becomes_failure_in_every_phase(monkeypatch, phase, relative):
    monkeypatch.setenv("ALPHAGSM_CI_WORKSHOP", "1")
    item = SimpleNamespace(path=runner.REPO_ROOT / relative)
    report = pytest.TestReport(
        nodeid=relative + "::test_case[process]",
        location=(relative, 1, "test_case"),
        keywords={}, outcome="skipped", longrepr=("test_file", 1, "SteamCMD unavailable"), when=phase,
    )
    report.wasxfail = "Expected failure must not disguise required CI validation"
    _finish_report_hook(item, report)
    assert report.failed and not report.skipped
    assert report.when == phase
    assert "Required anonymous Workshop CI case skipped" in report.longrepr
    assert report.nodeid in report.longrepr
    assert any(title == "Original Workshop skip" and "SteamCMD unavailable" in text
               for title, text in report.sections)
    assert not hasattr(report, "wasxfail")


@pytest.mark.parametrize("indicator,relative,outcome", [
    (None, "tests/integration_tests/test_wreckfestserver.py", "skipped"),
    ("0", "tests/integration_tests/test_wreckfestserver.py", "skipped"),
    ("1", "tests/integration_tests/test_authenticated_server.py", "skipped"),
    ("1", "tests/unit_tests/test_wreckfestserver.py", "skipped"),
    ("1", "tests/integration_tests/test_wreckfestserver.py", "passed"),
    ("1", "tests/integration_tests/test_wreckfestserver.py", "failed"),
])
def test_plugin_preserves_local_unrelated_and_existing_non_skip_results(
        monkeypatch, indicator, relative, outcome):
    if indicator is None:
        monkeypatch.delenv("ALPHAGSM_CI_WORKSHOP", raising=False)
    else:
        monkeypatch.setenv("ALPHAGSM_CI_WORKSHOP", indicator)
    item = SimpleNamespace(path=runner.REPO_ROOT / relative)
    report = pytest.TestReport(nodeid=relative + "::test_case", location=(relative, 1, "test_case"),
                               keywords={}, outcome=outcome, longrepr="original reason", when="call")
    _finish_report_hook(item, report)
    assert report.outcome == outcome
    assert report.longrepr == "original reason"
