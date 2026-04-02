"""Shared fixtures and helpers for AlphaGSM integration tests."""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"

# ---------------------------------------------------------------------------
# Override pytest-timeout for integration tests (default pytest.ini is 10s)
# ---------------------------------------------------------------------------
INTEGRATION_TEST_TIMEOUT = 1200  # 20 minutes per test function


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Give integration-marked tests a longer pytest-timeout."""
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT))


# ---------------------------------------------------------------------------
# Opt-in gates
# ---------------------------------------------------------------------------

def require_integration_opt_in():
    """Fail unless the integration flag is set."""
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.fail("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def require_steamcmd_opt_in():
    """Fail unless the SteamCMD integration flag is set."""
    if os.environ.get("ALPHAGSM_RUN_STEAMCMD") != "1":
        pytest.fail("Set ALPHAGSM_RUN_STEAMCMD=1 to run SteamCMD integration tests")


def require_command(name):
    """Fail if a required system command is not available."""
    if shutil.which(name) is None:
        pytest.fail(f"Required command not available: {name}")


def require_proton():
    """Fail if neither Wine nor Proton-GE is available on the host system.

    Imports ``utils.proton`` at call time so that game-module tests that call
    this helper do not pull in the module at collection time.
    """
    import sys
    import os as _os
    src_path = str(Path(__file__).resolve().parents[2] / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    import utils.proton as _proton  # pylint: disable=import-outside-toplevel
    if not _proton.is_available():
        pytest.fail(
            "Wine or Proton-GE is required to run Windows-binary servers; "
            "install with  scripts/install_proton.sh"
        )


def require_mysql(host="127.0.0.1", port=3306):
    """Skip if a MySQL/MariaDB server is not reachable on *host*:*port*."""
    try:
        with socket.create_connection((host, port), timeout=2):
            pass
    except OSError:
        pytest.skip(
            f"MySQL/MariaDB is not reachable at {host}:{port}; "
            "start a local database service to run this test"
        )


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------

def pick_free_tcp_port():
    """Return an ephemeral TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def pick_free_udp_port():
    """Return an ephemeral UDP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# ---------------------------------------------------------------------------
# Config / env helpers
# ---------------------------------------------------------------------------

def write_config(config_path, home_dir, session_tag="AlphaGSM-IT#"):
    """Write a minimal AlphaGSM config file pointing at *home_dir*."""
    work_dir = os.environ.get("ALPHAGSM_WORK_DIR")
    if work_dir:
        download_root = Path(work_dir).expanduser()
        db_path = download_root / "downloads" / "downloads.txt"
        target_path = download_root / "downloads" / "downloads"
    else:
        db_path = home_dir / "downloads" / "downloads.txt"
        target_path = home_dir / "downloads" / "downloads"
    config_path.write_text(
        "\n".join([
            "[core]",
            f"alphagsm_path = {home_dir}",
            f"userconf = {home_dir}",
            "",
            "[downloader]",
            f"db_path = {db_path}",
            f"target_path = {target_path}",
            "",
            "[server]",
            f"datapath = {home_dir / 'conf'}",
            "",
            "[screen]",
            f"screenlog_path = {home_dir / 'logs'}",
            f"sessiontag = {session_tag}",
            "keeplogs = 1",
            "",
        ]) + "\n"
    )


def alphagsm_env(config_path):
    """Return an environ dict configured for an integration test run."""
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


# ---------------------------------------------------------------------------
# AlphaGSM command runners
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 1200


def run_alphagsm(env, *args, timeout=DEFAULT_TIMEOUT):
    """Run the alphagsm script and return the CompletedProcess."""
    command = [sys.executable, str(ALPHAGSM_SCRIPT)] + list(args)
    return subprocess.run(
        command,
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def log_command_result(name, result):
    """Print a subprocess result for CI diagnostics."""
    print(f"\n=== {name} ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:")
        print(result.stdout.rstrip())
    if result.stderr:
        print("stderr:")
        print(result.stderr.rstrip())


def run_and_assert_ok(env, *args, timeout=DEFAULT_TIMEOUT):
    """Run alphagsm and assert a zero return code."""
    result = run_alphagsm(env, *args, timeout=timeout)
    log_command_result("alphagsm " + " ".join(args), result)
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


# ---------------------------------------------------------------------------
# Diagnostic helpers
# ---------------------------------------------------------------------------

def _dump_log(log_path, context="", max_lines=150):
    """Print the tail of *log_path* to captured stdout for CI diagnostics.

    Called before ``pytest.skip()`` so that developers can see exactly what
    the server printed (or nothing if the log was never created) without
    having to re-run the test locally.
    """
    try:
        p = Path(log_path)
        if not p.exists():
            print(f"[diagnostic] Log file not found ({context}): {log_path}")
            return
        text = p.read_text(errors="replace")
        lines = text.splitlines()
        size = p.stat().st_size
        print(
            f"[diagnostic] Log tail — {len(lines)} total lines, {size} bytes"
            + (f" [{context}]" if context else "")
            + f": {log_path}"
        )
        shown = lines[-max_lines:]
        for line in shown:
            print(f"  {line}")
        if len(lines) > max_lines:
            print(f"  ... ({len(lines) - max_lines} earlier lines omitted)")
    except OSError as exc:
        print(f"[diagnostic] Could not read log ({context}): {exc}")


# ---------------------------------------------------------------------------
# Wait helpers
# ---------------------------------------------------------------------------

def wait_for_log_marker(log_path, markers, timeout_seconds):
    """Poll a log file until one of *markers* appears; return the log text.

    On timeout dumps the full log tail to captured stdout and raises a test
    FAILURE so the problem is visible and must be fixed.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            log_text = log_path.read_text(errors="replace")
            if any(marker in log_text for marker in markers):
                return log_text
        time.sleep(2)
    _dump_log(log_path, context=f"looking for {markers!r}")
    pytest.fail(
        f"Log never showed readiness markers {markers!r} within {timeout_seconds}s: {log_path}"
    )


def wait_for_glob_log_marker(log_dir, glob_pattern, markers, timeout_seconds):
    """Poll files matching glob_pattern in log_dir until a marker appears.

    On timeout dumps the tail of every matching log file found.
    """
    deadline = time.time() + timeout_seconds
    log_dir_path = Path(log_dir)
    while time.time() < deadline:
        if log_dir_path.exists():
            for log_path in log_dir_path.glob(glob_pattern):
                try:
                    text = log_path.read_text(errors="replace")
                    if any(marker in text for marker in markers):
                        return text
                except OSError:
                    pass
        time.sleep(2)
    # Dump all matching log files for diagnostics.
    if log_dir_path.exists():
        matched = list(log_dir_path.glob(glob_pattern))
        if matched:
            for lp in matched:
                _dump_log(lp, context=f"glob timeout, looking for {markers!r}")
        else:
            print(f"[diagnostic] No files matching {glob_pattern!r} in {log_dir}")
    else:
        print(f"[diagnostic] Log dir not found: {log_dir}")
    pytest.fail(
        f"Log never showed readiness markers {markers!r} within {timeout_seconds}s in {log_dir}"
    )


def wait_for_tcp_closed(host, port, timeout_seconds):
    """Wait until a TCP connect to *host:port* fails."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                pass
        except Exception:  # noqa: BLE001
            return
        time.sleep(2)
    raise AssertionError(f"TCP port {host}:{port} still open after {timeout_seconds}s")


def wait_for_udp_closed(host, port, timeout_seconds):
    """Wait until a UDP Source query to *host:port* stops responding."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2)
            try:
                sock.sendto(b"\xFF\xFF\xFF\xFFTSource Engine Query\x00", (host, port))
                sock.recv(4096)
            except Exception:  # noqa: BLE001
                return
        time.sleep(2)
    raise AssertionError(f"UDP port {host}:{port} still responds after {timeout_seconds}s")

def wait_for_a2s_ready(host, port, timeout_seconds, log_path=None):
    """Poll A2S_INFO on *host*:*port* until the server responds.

    Retries until *timeout_seconds* elapses.  When the server starts returning
    a valid A2S response the function returns normally.  If *timeout_seconds*
    elapses without a successful response the test FAILS — the server must be
    fixed so it becomes query-ready within the allowed window.

    Optional *log_path* is printed (tail) on timeout for CI diagnostics.
    """
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from utils import query as query_utils  # pylint: disable=import-outside-toplevel
    # Asymmetric Phase 1 / Phase 2 timeouts for hibernating Source servers.
    #
    # Current SRCDS builds treat sv_hibernate as an unknown command, so the
    # server hibernates with an unknown inter-tick interval.  The A2S protocol
    # uses a two-phase challenge-response handshake: Phase 1 sends the initial
    # request and receives a challenge; Phase 2 immediately re-sends the
    # request with the challenge and waits for the final info response.
    #
    # Strategy: use a very short Phase 1 timeout (5 s) so retries happen
    # frequently — maximising the chance of catching the server during one of
    # its brief wake windows.  Once Phase 1 succeeds (server awake), Phase 2
    # uses a long timeout (120 s) to cover the full hibernation cycle before
    # the server wakes again to process the challenge response.
    _A2S_PHASE1_TIMEOUT = 5.0
    _A2S_PHASE2_TIMEOUT = 120.0
    deadline = time.time() + timeout_seconds
    last_exc = None
    while time.time() < deadline:
        try:
            query_utils.a2s_info(
                host, port,
                timeout=_A2S_PHASE1_TIMEOUT,
                phase2_timeout=_A2S_PHASE2_TIMEOUT,
            )
            return
        except query_utils.QueryError as exc:
            last_exc = exc
        # No additional sleep: Phase 1 already waits 5 s on timeout; Phase 2
        # (when it runs) takes up to 120 s, providing a natural gap.
    print(
        f"[diagnostic] A2S on {host}:{port} never responded within {timeout_seconds}s"
        f" — last error: {last_exc}"
    )
    if log_path is not None:
        _dump_log(log_path, context=f"A2S timeout on port {port}")
    pytest.fail(
        f"A2S on {host}:{port} never responded within {timeout_seconds}s: {last_exc}"
    )


def wait_for_tcp_open(host, port, timeout_seconds, log_path=None):
    """Poll a TCP connection to *host*:*port* until it is accepted.

    Retries every 2 seconds.  Returns normally once a connection succeeds.
    If *timeout_seconds* elapses without a successful connection the test
    FAILS — the server must be fixed so the port opens within the window.

    Optional *log_path* is printed (tail) on timeout for CI diagnostics.
    """
    import socket as _socket
    deadline = time.time() + timeout_seconds
    last_exc = None
    while time.time() < deadline:
        try:
            with _socket.create_connection((host, port), timeout=2):
                return
        except OSError as exc:
            last_exc = exc
            time.sleep(2)
    print(
        f"[diagnostic] TCP port {host}:{port} never opened within {timeout_seconds}s"
        f" — last error: {last_exc}"
    )
    if log_path is not None:
        _dump_log(log_path, context=f"TCP open timeout on port {port}")
    pytest.fail(f"TCP port {host}:{port} never opened within {timeout_seconds}s")


def wait_for_quake_ready(host, port, timeout_seconds, log_path=None):
    """Poll Quake UDP getstatus on *host*:*port* until the server responds.

    Retries every 2 seconds.  Returns normally once a valid status response
    is received.  If *timeout_seconds* elapses without a successful response
    the test FAILS — the server must be fixed so it becomes query-ready
    within the allowed window.

    Optional *log_path* is printed (tail) on timeout for CI diagnostics.
    """
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from utils import query as query_utils  # pylint: disable=import-outside-toplevel
    deadline = time.time() + timeout_seconds
    last_exc = None
    # Use a 10 s per-query timeout so that servers still loading their map
    # and assets have time to process and respond to the getstatus packet
    # without the query prematurely timing out at the default 2 s.
    _QUAKE_SOCKET_TIMEOUT = 10.0
    while time.time() < deadline:
        try:
            query_utils.quake_status(host, port, timeout=_QUAKE_SOCKET_TIMEOUT)
            return
        except query_utils.QueryError as exc:
            last_exc = exc
        time.sleep(2)
    print(
        f"[diagnostic] Quake status on {host}:{port} never responded within {timeout_seconds}s"
        f" — last error: {last_exc}"
    )
    if log_path is not None:
        _dump_log(log_path, context=f"Quake timeout on port {port}")
    pytest.fail(
        f"Quake status on {host}:{port} never responded within {timeout_seconds}s: {last_exc}"
    )

# ---------------------------------------------------------------------------
# SteamCMD skip helper
# ---------------------------------------------------------------------------

def skip_for_known_steamcmd_issue(result, app_id=None):
    """Skip the test only for expected, non-fixable reasons.

    All other failures (download errors, missing files, non-zero exit) are
    allowed to propagate to ``assert result.returncode == 0`` so they show up
    as visible test FAILURES rather than silent skips.  Tests listed as PASSED
    in ``docs/TEST_STATUS.md`` must not be silently hidden.
    """
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    # Only markers that make it impossible to run the test in CI at all
    # (authentication required, or module intentionally disabled) warrant a
    # skip.  Download/install failures should be visible as test failures.
    skip_markers = (
        "No subscription",
        "SteamCMD username required for this server",
        "is currently disabled",
    )
    for marker in skip_markers:
        if marker in combined:
            extra = f" (app {app_id})" if app_id else ""
            snippet = combined[:300].replace("\n", " | ")
            pytest.skip(
                f"Setup skipped — {marker!r} in output{extra}: {snippet}"
            )
