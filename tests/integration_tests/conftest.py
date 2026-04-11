"""Shared fixtures and helpers for AlphaGSM integration tests."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import pytest
from utils.steamcmd import _steamcmd_missing_manifest_flake

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

def pick_free_tcp_port(min_port=None, max_port=None):
    """Return a free TCP port on localhost, optionally constrained to a range."""

    if min_port is None and max_port is None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    min_port = 1024 if min_port is None else int(min_port)
    max_port = 65535 if max_port is None else int(max_port)
    for port in range(min_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free TCP port found in range {min_port}-{max_port}")


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
    download_root = home_dir / "downloads"
    work_dir = os.environ.get("ALPHAGSM_WORK_DIR")
    if work_dir and os.environ.get("ALPHAGSM_SHARE_DOWNLOAD_CACHE") == "1":
        download_root = Path(work_dir).expanduser() / "downloads"
    db_path = download_root / "downloads.txt"
    target_path = download_root / "downloads"
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
            "[runtime]",
            "backend = process",
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


def build_integration_tmp_path(test_name, tmp_path_factory):
    """Return the temp directory root for an integration test."""
    work_dir = os.environ.get("ALPHAGSM_WORK_DIR")
    if not work_dir:
        return tmp_path_factory.mktemp(test_name)

    root = Path(work_dir).expanduser() / "pytest-integration"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{test_name}-", dir=str(root)))


@pytest.fixture
def tmp_path(request, tmp_path_factory):
    """Create and clean integration-test temp dirs under ``ALPHAGSM_WORK_DIR``."""
    path = build_integration_tmp_path(request.node.name, tmp_path_factory)
    try:
        yield path
    finally:
        if os.environ.get("ALPHAGSM_KEEP_INTEGRATION_TMP") == "1":
            return
        shutil.rmtree(path, ignore_errors=True)


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


def wait_for_info_protocol(env, server_name, expected_protocol, timeout_seconds):
    """Poll ``info --json`` until it returns *expected_protocol*."""
    deadline = time.time() + timeout_seconds
    last_result = None
    last_data = None
    while time.time() < deadline:
        result = run_alphagsm(env, server_name, "info", "--json", timeout=120)
        last_result = result
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                data = None
            else:
                last_data = data
                if data.get("protocol") == expected_protocol:
                    return data
        time.sleep(5)

    log_command_result(
        "alphagsm " + " ".join((server_name, "info", "--json")),
        last_result,
    )
    pytest.fail(
        f"info --json never returned protocol {expected_protocol!r} within {timeout_seconds}s: "
        f"last payload={last_data!r}"
    )


def read_info_json(env, server_name):
    """Run ``info --json`` and return the parsed payload."""
    result = run_and_assert_ok(env, server_name, "info", "--json")
    return json.loads(result.stdout.strip())


def find_source_server_cfg(install_dir):
    """Return the single Source ``cfg/server.cfg`` under *install_dir*."""
    candidates = sorted(Path(install_dir).glob("**/cfg/server.cfg"))
    assert candidates, f"Expected cfg/server.cfg under {install_dir}"
    return candidates[0]


def set_source_hibernation(server_cfg_path, enabled):
    """Force Source hibernation on or off in ``server.cfg``."""
    cfg_text = Path(server_cfg_path).read_text(encoding="utf-8")
    target = "sv_hibernate_when_empty 0"
    replacement = "sv_hibernate_when_empty 1" if enabled else target
    if enabled:
        if target in cfg_text:
            cfg_text = cfg_text.replace(target, replacement)
        elif replacement not in cfg_text:
            cfg_text += "\nsv_hibernate_when_empty 1\n"
    else:
        cfg_text = cfg_text.replace("sv_hibernate_when_empty 1", target)
        if target not in cfg_text:
            cfg_text += "\nsv_hibernate_when_empty 0\n"
    Path(server_cfg_path).write_text(cfg_text, encoding="utf-8")


def assert_source_server_empty(data):
    """Assert a fresh Source server reports no human players or bots."""
    assert data.get("players") == 0, f"Expected 0 players on fresh server: {data!r}"
    if "bots" in data:
        assert data.get("bots") == 0, f"Expected 0 bots on fresh server: {data!r}"


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

def wait_for_a2s_ready(host, port, timeout_seconds, log_path=None, tcp_port=None):
    """Poll A2S_INFO on *host*:*port* until the server responds.

    Retries until *timeout_seconds* elapses.  When the server starts returning
    a valid A2S response the function returns normally.  If *timeout_seconds*
    elapses without a successful response the test FAILS — the server must be
    fixed so it becomes query-ready within the allowed window.

    Optional *log_path* is printed (tail) on timeout for CI diagnostics.

    Optional *tcp_port* overrides the TCP port used for timeout diagnostics.
    Use this when the A2S query port (``port``) differs from the game's TCP
    port so the failure message can report whether the game's TCP listener is
    reachable while A2S is still failing.
    """
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from utils import query as query_utils  # pylint: disable=import-outside-toplevel
    # Asymmetric Phase 1 / Phase 2 timeouts for hibernating Source servers.
    #
    # Current SRCDS builds treat sv_hibernate as an unknown command, so the
    # server hibernates with an inter-tick interval that varies by game.
    # Measured hibernation tick intervals in Docker CI range from ~5 s to
    # ~12 s.  The A2S protocol uses a two-phase challenge-response handshake:
    # Phase 1 sends the initial request and receives a challenge; Phase 2
    # immediately re-sends the request with the challenge and waits for the
    # final info response.
    #
    # Strategy: use a Phase 1 timeout (15 s) long enough to catch the server
    # during one hibernation tick (up to ~12 s) — maximising the chance of
    # receiving the challenge reply.  Once Phase 1 succeeds (server awake),
    # Phase 2 uses a long timeout (120 s) to cover the full hibernation cycle
    # before the server wakes again to process the challenge response.
    _A2S_PHASE1_TIMEOUT = 15.0
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
        # No additional sleep: Phase 1 already waits 15 s on timeout; Phase 2
        # (when it runs) takes up to 120 s, providing a natural gap.

    _tcp_check_port = tcp_port if tcp_port is not None else port
    tcp_diag = None
    try:
        with socket.create_connection((host, _tcp_check_port), timeout=5):
            tcp_diag = f"TCP port {host}:{_tcp_check_port} is open"
    except OSError as exc:
        tcp_diag = f"TCP probe on {host}:{_tcp_check_port} failed: {exc}"

    if log_path is not None and Path(log_path).exists() and Path(log_path).stat().st_size > 0:
        print(
            f"[diagnostic] Log file exists for failed A2S readiness check: {log_path}"
            f" ({Path(log_path).stat().st_size} bytes)"
        )
    print(
        f"[diagnostic] A2S on {host}:{port} never responded within {timeout_seconds}s"
        f" — last error: {last_exc}"
        + (f" — {tcp_diag}" if tcp_diag else "")
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


def wait_for_udp_open(host, port, timeout_seconds, log_path=None):
    """Poll a generic UDP reachability probe until *host*:*port* responds.

    Retries every 2 seconds. Returns normally once the UDP listener is deemed
    reachable. If *timeout_seconds* elapses first the test FAILS.

    Optional *log_path* is printed (tail) on timeout for CI diagnostics.
    """
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from utils import query as query_utils  # pylint: disable=import-outside-toplevel

    deadline = time.time() + timeout_seconds
    last_exc = None
    while time.time() < deadline:
        try:
            query_utils.udp_ping(host, port)
            return
        except query_utils.QueryError as exc:
            last_exc = exc
            time.sleep(2)
    print(
        f"[diagnostic] UDP port {host}:{port} never opened within {timeout_seconds}s"
        f" — last error: {last_exc}"
    )
    if log_path is not None:
        _dump_log(log_path, context=f"UDP open timeout on port {port}")
    pytest.fail(f"UDP port {host}:{port} never opened within {timeout_seconds}s")


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

    if _steamcmd_missing_manifest_flake(combined, app_id):
        extra = f" (app {app_id})" if app_id else ""
        snippet = combined[:300].replace("\n", " | ")
        pytest.skip(
            f"SteamCMD flake skip — repeated Missing configuration/state 0x202 during setup{extra}: {snippet}"
        )

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
