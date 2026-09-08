"""Exercise smoke outcomes with mocked commands, without launching any server."""

import os
import re
import shlex
import subprocess
import sys

import pytest

from tests.helpers import REPO_ROOT


SMOKE_DIR = REPO_ROOT / "tests/smoke_tests"
HELPERS = SMOKE_DIR / "steamcmd_helpers.sh"
MINECRAFT_RUNNERS = tuple(
    path for path in sorted(SMOKE_DIR.glob("run_*.sh"))
    if '"$STATUS_HELPER" wait-for-' in path.read_text()
    and path.name != "run_tf2.sh"
)


def _shell(body, **env):
    return subprocess.run(
        ["bash", "-c", "set -Eeuo pipefail\n" + body],
        env=dict(os.environ, **env), capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("path", sorted(SMOKE_DIR.glob("run_*.sh")), ids=lambda p: p.stem)
def test_declared_skip_preambles_return_77(path):
    """Run only the inert preamble, never the preserved lifecycle below it."""
    preamble = path.read_text().split("set -Eeuo pipefail", 1)[0]
    if not re.search(r"^exit \d+$", preamble, re.MULTILINE):
        return
    assert _shell(preamble).returncode == 77


@pytest.mark.parametrize("helper", [
    "run_create_or_skip_disabled test create fixture",
    "run_setup_or_skip_steamcmd test setup -n 12345 /unused",
    "run_alphagsm_or_skip_supported_prereq test start",
    "run_start_with_port_retry test",
])
@pytest.mark.parametrize("message,expected", [
    ("ENABLED (BYO): provide owned files", 77),
    ("ENABLED (AUTH): provide a provider token", 77),
    ("No such file or directory", 23),
    ("Failed to install app (Missing configuration)", 23),
    ("Error extracting download", 23),
    ("returned non-zero exit status", 23),
    ("Temporary failure in name resolution", 23),
    ("no space left on device", 23),
])
def test_command_helpers_distinguish_prerequisites_from_failures(helper, message, expected):
    result = _shell(
        f"source {shlex.quote(str(HELPERS))}\n"
        'run_alphagsm() { printf "%s\\n" "$MESSAGE"; return 23; }\n' + helper,
        MESSAGE=message,
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize("helper", [
    "require_proton", "require_command_or_skip missing_fixture_command",
])
def test_missing_host_prerequisites_return_77(helper):
    result = _shell(f"source {shlex.quote(str(HELPERS))}\ncommand() {{ return 1; }}\n{helper}")
    assert result.returncode == 77


def test_disabled_create_returns_77():
    result = _shell(
        f"source {shlex.quote(str(HELPERS))}\n"
        'run_alphagsm() { echo "fixture is currently disabled"; return 1; }\n'
        "run_create_or_skip_disabled test create fixture"
    )
    assert result.returncode == 77


@pytest.mark.parametrize("rc", [0, 19])
def test_stop_preserves_command_result_even_when_diagnostics_fail(rc):
    result = _shell(
        f"source {shlex.quote(str(HELPERS))}\n"
        'run_alphagsm() { if [[ "$2" == stop ]]; then return "$STOP_RC"; fi; return 4; }\n'
        "run_stop_or_skip test", STOP_RC=str(rc),
    )
    assert result.returncode == rc


@pytest.mark.parametrize("path", MINECRAFT_RUNNERS, ids=lambda p: p.stem)
@pytest.mark.parametrize("failed_stage", ["status", "closed", "none"])
def test_minecraft_lifecycle_propagates_readiness_and_shutdown_failures(path, failed_stage):
    script = path.read_text()
    lifecycle = script[script.index('run_alphagsm "$SERVER_NAME" start'):]
    result = _shell('''
SERVER_NAME=fixture
SERVER_STARTED=0
PORT=12345
START_TIMEOUT_SECONDS=0
STOP_TIMEOUT_SECONDS=0
PYTHON_BIN=mock_status
STATUS_HELPER=unused
run_alphagsm() { :; }
run_stop_or_skip() { :; }
mock_status() { if [[ "$2" == *"$FAILED_STAGE" ]]; then return 17; fi; }
''' + lifecycle, FAILED_STAGE=failed_stage)
    assert (result.returncode == 0) == (failed_stage == "none"), result.stdout + result.stderr
    assert result.returncode != 77


def test_heat_timeout_is_failure():
    script = (SMOKE_DIR / "run_heatserver.sh").read_text()
    helper = script[script.index("wait_for_heat_ready() {"):script.index('require_cmd "$PYTHON_BIN"')]
    result = _shell(helper + "\nwait_for_heat_ready /nonexistent/heat-fixture 0")
    assert result.returncode == 1
    assert "skipping" not in result.stderr


def test_tf2_setup_errors_cannot_be_reported_as_success_or_skip():
    script = (SMOKE_DIR / "run_tf2.sh").read_text()
    setup = script[script.index('run_alphagsm "$SERVER_NAME" create'):script.index('if [[ ! -f "$INSTALL_DIR/srcds_run_64"')]
    result = _shell(f"source {shlex.quote(str(HELPERS))}\n" + '''
SERVER_NAME=fixture
PORT=12345
INSTALL_DIR=/unused
run_alphagsm() {
  if [[ "$2" == setup ]]; then
    echo "tf/cfg/server.cfg: No such file or directory"
    return 23
  fi
}
''' + setup)
    assert result.returncode == 23


@pytest.mark.parametrize("payload,command_rc,expected", [
    ('{"protocol": "a2s"}', 0, 0),
    ('{"protocol": "tcp"}', 0, 1),
    ('{"protocol": "a2s"}', 8, 1),
    ('not json', 0, 1),
])
def test_protocol_wait_checks_real_payload_and_command_status(tmp_path, payload, command_rc, expected):
    fake_cli = tmp_path / "fake_cli.py"
    fake_cli.write_text("import os\nprint(os.environ['PAYLOAD'])\nraise SystemExit(int(os.environ['COMMAND_RC']))\n")
    result = _shell(
        f"source {shlex.quote(str(HELPERS))}\n"
        'sleep() { SECONDS=$((SECONDS + 10)); }\n'
        'run_alphagsm() { echo "diagnostic $*"; }\n'
        "wait_for_info_protocol fixture a2s 5",
        ALPHAGSM_SCRIPT=str(fake_cli), CONFIG_PATH="/unused",
        REPO_ROOT=str(REPO_ROOT), PYTHON_BIN=sys.executable,
        PAYLOAD=payload, COMMAND_RC=str(command_rc),
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize("module", [
    "bb2server", "bmdmserver", "ccserver", "cssserver",
    "dodsserver", "doiserver", "emserver", "fofserver", "gmodserver",
    "hl2dmserver", "hldmsserver", "insserver", "l4dserver", "l4d2server",
    "nmrihserver", "pvkiiserver",
])
def test_source_smoke_config_keeps_server_awake(module):
    script = (SMOKE_DIR / f"run_{module}.sh").read_text()
    config = script.split('cat > "$CONFIG_PATH" <<EOF\n', 1)[1].split("\nEOF", 1)[0]
    assert f"[gamemodules.{module}.servercfg]\nsv_hibernate_when_empty = 0" in config


@pytest.mark.parametrize("module,cfg", [
    ("tf2", "tf/cfg/server.cfg"), ("counterstrike2", "game/csgo/cfg/server.cfg"),
])
def test_custom_source_smoke_writes_native_hibernation_override(tmp_path, module, cfg):
    script = (SMOKE_DIR / f"run_{module}.sh").read_text()
    native_config = tmp_path / cfg
    native_config.parent.mkdir(parents=True)
    native_config.write_text("hostname Fixture\n")
    writes = [line for line in script.splitlines() if line.startswith("printf ")]
    assert writes
    result = _shell("\n".join(writes), INSTALL_DIR=str(tmp_path))
    assert result.returncode == 0
    assert "sv_hibernate_when_empty 0" in native_config.read_text()


@pytest.mark.parametrize("exports,expected", [
    ("unset", 77), ("missing", 1), ("empty", 1), ("complete", 0),
])
def test_ets2_export_prerequisite_is_checked_before_setup(tmp_path, exports, expected):
    script = (SMOKE_DIR / "run_ets2server.sh").read_text()
    prefix = script.split("require_ets2_exports() {", 1)[1]
    helper = "require_ets2_exports() {" + prefix.split("\n}\n", 1)[0] + "\n}\n"
    if exports in ("empty", "complete"):
        for name in ("server_packages.sii", "server_packages.dat"):
            (tmp_path / name).write_text("fixture" if exports == "complete" else "")
    result = _shell(
        helper + "require_ets2_exports",
        ALPHAGSM_ETS2_SERVER_PACKAGES_DIR="" if exports == "unset" else str(tmp_path),
    )
    assert result.returncode == expected
    assert ("SKIPPED" in result.stderr) == (exports == "unset")
    assert script.index("\nrequire_ets2_exports\n") < script.index("\nWORK_DIR=")


def test_application_log_capture_includes_game_errors(tmp_path):
    log = tmp_path / "SpaceEngineersDedicated.log"
    log.write_text("fixture game startup exception\n")
    result = _shell(
        f"source {shlex.quote(str(HELPERS))}\n"
        f"capture_application_logs {shlex.quote(str(log))} /nonexistent/fixture.log"
    )
    assert result.returncode == 0
    assert "fixture game startup exception" in result.stderr
    assert str(log) in result.stderr


@pytest.mark.parametrize("rc", [0, 77, 14])
@pytest.mark.parametrize("selection", [[], ["SMOKE_TEST=run_fixture.sh"]], ids=["all", "single"])
def test_make_smoke_preserves_failure_and_accepts_skip(tmp_path, rc, selection):
    """The recipe runs only a fixture that returns an exit code."""
    smoke_dir = tmp_path / "tests/smoke_tests"
    smoke_dir.mkdir(parents=True)
    (smoke_dir / "run_fixture.sh").write_text(f"exit {rc}\n")
    makefile = (REPO_ROOT / "Makefile").read_text()
    recipe = makefile[makefile.index("smoke-test:\n"):].split("\n\n", 1)[0]
    (tmp_path / "Makefile").write_text(recipe + "\n")
    result = subprocess.run(
        ["make", "smoke-test", *selection], cwd=tmp_path,
        capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == (rc in (0, 77))
    if rc == 77:
        assert "SKIPPED" in result.stdout
