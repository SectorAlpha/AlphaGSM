"""Shared fixtures and helpers for AlphaGSM integration tests."""

import importlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time

import pytest
from scripts import select_test_port
from utils.steamcmd import _steamcmd_state_202_flake

_CONTROL_EXCEPTIONS = (KeyboardInterrupt, SystemExit, GeneratorExit)

REPO_ROOT = Path(__file__).resolve().parents[2]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"
DEFAULT_INTEGRATION_WORK_DIR = Path("/tmp/alphagsm-work")
DOCKER_ROUTE_FILE = "/proc/net/route"


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


def require_command_or_skip(name, reason=None):
    """Skip if an optional host command is not available."""

    if shutil.which(name) is None:
        pytest.skip(reason or f"Required command not available: {name}")


def resolve_runtime_image(configured_env_var, local_image, published_image):
    """Prefer a configured, local, then published Docker runtime image."""

    configured_image = os.environ.get(configured_env_var)
    if configured_image:
        return configured_image

    local_result = subprocess.run(
        ["docker", "image", "inspect", local_image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if local_result.returncode == 0:
        return local_image

    return published_image


def resolve_steamcmd_linux_runtime_image():
    """Prefer an explicit or local SteamCMD Linux runtime image when available."""

    return resolve_runtime_image(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX",
        "alphagsm-steamcmd-linux-runtime:test",
        "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest",
    )


def resolve_wine_proton_runtime_image():
    """Prefer an explicit or local Wine/Proton runtime image when available."""

    return resolve_runtime_image(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON",
        "alphagsm-wine-proton-runtime:test",
        "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest",
    )


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


def _docker_bridge_gateway():
    """Return the default Docker bridge gateway for a containerized test runner."""

    if not os.path.exists("/.dockerenv"):
        return None
    try:
        route_text = Path(DOCKER_ROUTE_FILE).read_text(encoding="ascii")
    except (OSError, UnicodeError):
        return None

    for line in route_text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 3 or fields[1] != "00000000":
            continue
        try:
            gateway_bytes = struct.pack("<L", int(fields[2], 16))
            return socket.inet_ntoa(gateway_bytes)
        except (OSError, ValueError, struct.error):
            continue
    return None


def _runtime_probe_hosts(host):
    """Return endpoint hosts needed from a process or Docker test runner.

    GitHub integration tests run inside a manager container. In that context
    loopback reaches process-runtime servers, while a published sibling
    Docker container is reachable through the manager's bridge gateway.
    """

    hosts = [str(host)]
    if os.path.exists("/.dockerenv"):
        for candidate in ("127.0.0.1", _docker_bridge_gateway()):
            if candidate and candidate not in hosts:
                hosts.append(candidate)
    return tuple(hosts)


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------

def pick_free_tcp_port(min_port=None, max_port=None):
    """Return a free TCP port on localhost, optionally constrained to a range.

    The chosen port is verified to be bindable on both TCP and UDP (without
    SO_REUSEADDR) so that AlphaGSM's port-manager pre-flight check, which
    probes both protocols, will not reject it.
    """
    selector_options = {"port_is_free": select_test_port.port_free_for_both}
    if min_port is not None:
        selector_options["min_port"] = int(min_port)
    if max_port is not None:
        selector_options["max_port"] = int(max_port)
    return select_test_port.pick_free_port_group(1, **selector_options)


def pick_free_tcp_port_group(count):
    """Return the first port in a free consecutive TCP+UDP port range."""

    return select_test_port.pick_free_port_group(
        count,
        port_is_free=select_test_port.port_free_for_both,
    )


def pick_free_udp_port():
    """Return a non-ephemeral UDP port on localhost.

    The chosen port is verified to be bindable on both UDP and TCP (without
    SO_REUSEADDR) so that AlphaGSM's port-manager pre-flight check, which
    probes both protocols, will not reject it.  This catches ports in TCP
    TIME_WAIT state that the OS would otherwise return as 'free for UDP'.
    """
    return select_test_port.pick_free_port_group(
        1,
        port_is_free=select_test_port.port_free_for_both,
    )


_PORT_CONFLICT_MARKERS = (
    "claimed ports are not free",
    "Live listener already holds",
    "Port conflicts detected",
)


def _parse_recommended_port_overrides(output):
    """Return recommended claim overrides from AlphaGSM's conflict hint.

    Parses the ``Recommended free port set:`` line and returns a mapping of
    bare ``key=value`` pairs as integers. Returns an empty dict if the line is
    absent or contains no parseable values.
    """
    idx = output.find("Recommended free port set:")
    if idx == -1:
        return {}
    line = output[idx:].splitlines()[0]
    return {
        key: int(value)
        for key, value in re.findall(r"\b([a-z][a-z0-9_]*)=(\d+)\b", line)
    }


def run_setup_with_port_retry(env, server_name, port, install_dir, *extra_flags,
                               timeout=None, max_tries=3, steam_app_id=None):
    """Run ``setup -n <port> <install_dir>`` and retry with a new port on conflict.

    If setup fails because the port is already in use (AlphaGSM port-manager
    pre-flight), a new port is chosen — preferring the port recommended by
    AlphaGSM's own output — and setup is retried up to *max_tries* times.

    Returns ``(result, final_port)`` where *final_port* is the port that was
    ultimately accepted (which may differ from the original *port*).

    ``steam_app_id`` keeps known SteamCMD flake classification explicit when
    setup never reaches the port-conflict retry path.
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    current_port = port
    last_result = None
    result = None
    set_result = None
    command_parts = []
    combined = ""
    recommended = {}
    try:
        for _attempt in range(max_tries):
            command_parts = [
                server_name, "setup", "-n", str(current_port), str(install_dir),
                *map(str, extra_flags),
            ]
            result = run_alphagsm(
                env, *command_parts, timeout=timeout,
            )
            log_command_result(
                "alphagsm " + " ".join(command_parts) + f" [timeout={timeout}]",
                result,
            )
            last_result = result
            if result.returncode == 0:
                return _redact_subprocess_diagnostic(result), current_port
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            if not any(m in combined for m in _PORT_CONFLICT_MARKERS):
                break
            recommended = _parse_recommended_port_overrides(combined)
            current_port = recommended.get("port", pick_free_tcp_port())
            for key, value in recommended.items():
                if key == "port":
                    continue
                set_result = run_alphagsm(
                    env, server_name, "set", key, str(value), timeout=timeout,
                )
                log_command_result(
                    f"alphagsm {server_name} set {key} {value} [timeout={timeout}]",
                    set_result,
                )
                if set_result.returncode != 0:
                    last_result = set_result
                    break
            else:
                continue
            break
        if steam_app_id is None:
            skip_for_known_steamcmd_issue(last_result)
        else:
            skip_for_known_steamcmd_issue(last_result, app_id=steam_app_id)
        assert_alphagsm_result_ok(last_result)
        return last_result, current_port  # unreachable after failure
    finally:
        if sys.exc_info()[0] is not None:
            env = None
            server_name = None
            install_dir = None
            extra_flags = _redact_command_args(extra_flags)
            command_parts = list(_redact_command_args(command_parts))
            result = _redact_subprocess_diagnostic(result)
            set_result = _redact_subprocess_diagnostic(set_result)
            last_result = _redact_subprocess_diagnostic(last_result)
            combined = _redact_logged_text(combined)
            recommended = {}


# ---------------------------------------------------------------------------
# Config / env helpers
# ---------------------------------------------------------------------------

def _load_runtime_module(module_name, servermodulespackage="gamemodules."):
    """Return the imported module used to probe runtime capability."""

    module_name = str(module_name or "").strip()
    if not module_name:
        raise ImportError("Module name is required")

    servermodulespackage = str(servermodulespackage or "gamemodules.")
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    if servermodulespackage == "gamemodules.":
        from server.server import find_module  # pylint: disable=import-outside-toplevel

        _resolved_name, module = find_module(module_name)
        return module

    return importlib.import_module(servermodulespackage + module_name)


def _module_uses_explicit_docker_runtime(module_name, servermodulespackage="gamemodules."):
    """Return whether *module_name* declares an explicit Docker runtime contract."""

    try:
        module = _load_runtime_module(
            module_name,
            servermodulespackage=servermodulespackage,
        )
    except Exception:  # pragma: no cover - kept intentionally defensive for test setup
        return False

    import server.runtime as runtime_module  # pylint: disable=import-outside-toplevel

    return (
        runtime_module._has_explicit_module_hook(module, "get_runtime_requirements")
        and runtime_module._has_explicit_module_hook(module, "get_container_spec")
    )


def default_runtime_backend():
    """Return the default runtime backend for integration tests.

    Local runs stay process-first to preserve the traditional developer
    workflow. GitHub Actions uses ``auto`` so Docker-capable modules exercise
    their declared runtime contract during CI without each test hardcoding a
    Docker-only default.
    """

    return "auto" if os.environ.get("GITHUB_ACTIONS") == "true" else "process"


def effective_runtime_backend(
    runtime_backend="process",
    *,
    module_name=None,
    servermodulespackage="gamemodules.",
):
    """Return the effective runtime backend for an integration test config."""
    if runtime_backend != "auto":
        return runtime_backend
    return (
        "docker"
        if _module_uses_explicit_docker_runtime(
            module_name,
            servermodulespackage=servermodulespackage,
        )
        else "process"
    )


def require_command_for_runtime(
    name,
    *,
    runtime_backend="process",
    module_name=None,
    servermodulespackage="gamemodules.",
):
    """Require *name* only when the effective integration runtime is process."""
    if effective_runtime_backend(
        runtime_backend,
        module_name=module_name,
        servermodulespackage=servermodulespackage,
    ) == "process":
        require_command(name)


def write_config(
    config_path,
    home_dir,
    session_tag="AlphaGSM-IT#",
    *,
    backend="screen",
    runtime_backend="process",
    docker_backend="subprocess",
    module_name=None,
    servermodulespackage="gamemodules.",
):
    """Write a minimal AlphaGSM config file pointing at *home_dir*."""
    download_root = home_dir / "downloads"
    work_dir = os.environ.get("ALPHAGSM_WORK_DIR")
    if work_dir and os.environ.get("ALPHAGSM_SHARE_DOWNLOAD_CACHE") == "1":
        download_root = Path(work_dir).expanduser() / "downloads"
    db_path = download_root / "downloads.txt"
    target_path = download_root / "downloads"
    selected_runtime_backend = effective_runtime_backend(
        runtime_backend,
        module_name=module_name,
        servermodulespackage=servermodulespackage,
    )
    config_lines = [
        "[core]",
        f"alphagsm_path = {home_dir}",
        f"userconf = {home_dir}",
        "",
        "[downloader]",
        f"db_path = {db_path}",
        f"target_path = {target_path}",
        "",
    ]
    if work_dir:
        config_lines.extend(
            [
                "[downloader.steamcmd]",
                f"steamcmd_path = {Path(work_dir).expanduser() / 'steamcmd'}",
                "",
            ]
        )
    config_lines.extend(
        [
            "[server]",
            f"datapath = {home_dir / 'conf'}",
            f"servermodulespackage = {servermodulespackage}",
            "",
            "[runtime]",
            f"backend = {selected_runtime_backend}",
            "",
            "[process]",
            f"backend = {backend}",
            "",
            "[docker]",
            f"backend = {docker_backend}",
            "",
            "[screen]",
            f"screenlog_path = {home_dir / 'logs'}",
            f"sessiontag = {session_tag}",
            "keeplogs = 1",
            "",
        ]
    )
    config_path.write_text("\n".join(config_lines) + "\n")


class _SecretSafeEnvironment(dict):
    """Environment mapping with exact values and a redacted diagnostic repr."""

    def __repr__(self):
        safe_values = {
            key: (
                "<redacted>"
                if _looks_sensitive_cli_key(key)
                else _redact_logged_text(value)
            )
            for key, value in self.items()
        }
        return repr(safe_values)

    __str__ = __repr__

    def copy(self):
        return type(self)(self)


def alphagsm_env(config_path):
    """Return an environ mapping configured for an integration test run."""
    env = _SecretSafeEnvironment(os.environ)
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    if env.get("ALPHAGSM_BINARY"):
        env["ALPHAGSM_BINARY"] = str(Path(env["ALPHAGSM_BINARY"]).expanduser().resolve())
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
    else:
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def alphagsm_command(env):
    """Select a supplied standalone executable, preserving the source default."""
    if env.get("ALPHAGSM_BINARY"):
        return [str(Path(env["ALPHAGSM_BINARY"]).expanduser().resolve())]
    return [sys.executable, str(ALPHAGSM_SCRIPT)]


def build_integration_tmp_path(test_name, _tmp_path_factory):
    """Return the temp directory root for an integration test."""
    work_dir = os.environ.get("ALPHAGSM_WORK_DIR")
    root = (
        Path(work_dir).expanduser()
        if work_dir
        else DEFAULT_INTEGRATION_WORK_DIR
    ) / "pytest-integration"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{test_name}-", dir=str(root)))


@pytest.fixture
def tmp_path(request, tmp_path_factory):
    """Create and clean integration-test temp dirs under the shared work root."""
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


def _looks_sensitive_cli_key(value):
    lowered = str(value).lower()
    normalized = re.sub(r"[^a-z0-9]", "", lowered)
    if not normalized:
        return False
    if normalized in {
        "authorization",
        "authorizationheader",
        "privatekey",
        "sshprivatekey",
    }:
        return True
    sensitive_parts = {
        "password",
        "passwd",
        "passphrase",
        "token",
        "secret",
        "apikey",
        "licensekey",
        "invitecode",
        "joincode",
    }
    parts = {part for part in re.split(r"[^a-z0-9]+", lowered) if part}
    if parts & sensitive_parts:
        return True
    sensitive_suffixes = (
        "password",
        "passwd",
        "passphrase",
        "token",
        "secret",
        "apikey",
        "licensekey",
        "invitecode",
        "joincode",
    )
    return any(normalized.endswith(suffix) for suffix in sensitive_suffixes)


def _redact_command_args(command_args):
    redacted = []
    arguments = tuple(map(str, command_args))
    index = 0
    while index < len(arguments):
        text = arguments[index]
        if "=" in text:
            key, _value = text.split("=", 1)
            if _looks_sensitive_cli_key(key):
                redacted.append(f"{key}=<redacted>")
                index += 1
                continue
        if (
            re.fullmatch(r"-{0,2}[A-Za-z0-9_.-]+", text)
            and _looks_sensitive_cli_key(text)
        ):
            redacted.append(text)
            normalized = re.sub(r"[^a-z0-9]", "", text.lower())
            index += 1
            if normalized in {"authorization", "authorizationheader"}:
                while index < len(arguments) and not arguments[index].startswith("-"):
                    redacted.append("<redacted>")
                    index += 1
                continue
            if index < len(arguments):
                redacted.append("<redacted>")
                index += 1
            continue
        redacted.append(_redact_logged_text(text))
        index += 1
    return tuple(redacted)


def _format_logged_command(name, command_args=None):
    if command_args is None:
        return name
    rendered_args = " ".join(_redact_command_args(command_args))
    if not rendered_args:
        return name
    return f"{name} {rendered_args}"


def _quote_delimiter_at(text, index):
    """Return ``(slash_count, quote, content_start)`` at *index*, if quoted."""

    cursor = index
    while cursor < len(text) and text[cursor] == "\\":
        cursor += 1
    if cursor < len(text) and text[cursor] in {'"', "'"}:
        return cursor - index, text[cursor], cursor + 1
    return None


def _find_quoted_end(text, content_start, slash_count, quote):
    """Find an escape-layer-aware closing quote for a logged value."""

    cursor = content_start
    escape_unit = slash_count + 1
    while cursor < len(text):
        quote_index = text.find(quote, cursor)
        if quote_index < 0:
            return None
        run_start = quote_index
        while run_start > content_start and text[run_start - 1] == "\\":
            run_start -= 1
        run_length = quote_index - run_start
        extra_slashes = run_length - slash_count
        if (
            extra_slashes >= 0
            and extra_slashes % escape_unit == 0
            and (extra_slashes // escape_unit) % 2 == 0
        ):
            return quote_index - slash_count, quote_index + 1
        cursor = quote_index + 1
    return None


def _parse_logged_key(text, index):
    """Return the end and metadata of a sensitive key at *index*."""

    if index > 0 and (text[index - 1].isalnum() or text[index - 1] in "_-"):
        return None

    cursor = index
    prefixed = False
    if text.startswith("--", cursor):
        cursor += 2
        prefixed = True
    elif text.startswith("-", cursor):
        cursor += 1
        prefixed = True

    delimiter = _quote_delimiter_at(text, cursor)
    if delimiter is not None:
        slash_count, quote, content_start = delimiter
        closing = _find_quoted_end(text, content_start, slash_count, quote)
        if closing is None:
            return None
        content_end, after_key = closing
        key = text[content_start:content_end]
        if _looks_sensitive_cli_key(key):
            normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
            return after_key, (normalized_key, (slash_count, quote))
        return None

    key_start = cursor
    while cursor < len(text) and (
        text[cursor].isalnum() or text[cursor] in "_.-"
    ):
        cursor += 1
    if cursor == key_start:
        return None
    key = text[key_start:cursor]
    if _looks_sensitive_cli_key(key):
        value_cursor = cursor
        while value_cursor < len(text) and text[value_cursor] in " \t":
            value_cursor += 1
        normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
        ambiguous_bare_keys = {
            "password",
            "passwd",
            "passphrase",
            "token",
            "secret",
            "authorization",
            "authorizationheader",
            "privatekey",
            "sshprivatekey",
        }
        if (
            prefixed
            or (value_cursor < len(text) and text[value_cursor] in ":=")
            or any(character in key for character in "_.-")
            or normalized_key not in ambiguous_bare_keys
        ):
            return cursor, (normalized_key, None)

    whitespace_end = cursor
    while whitespace_end < len(text) and text[whitespace_end] in " \t":
        whitespace_end += 1
    second_start = whitespace_end
    while whitespace_end < len(text) and (
        text[whitespace_end].isalnum() or text[whitespace_end] in "_.-"
    ):
        whitespace_end += 1
    spaced_key = re.sub(
        r"[^a-z0-9]",
        "",
        (key + text[second_start:whitespace_end]).lower(),
    )
    if second_start < whitespace_end and spaced_key in {
        "apikey",
        "licensekey",
        "invitecode",
        "joincode",
    }:
        return whitespace_end, (spaced_key, None)
    return None


_PRIVATE_KEY_BEGIN = re.compile(r"-----BEGIN ([A-Z0-9 ]*PRIVATE KEY)-----")


def _private_key_block_end(text, value_start):
    """Return the matching private-key block end, failing closed if truncated."""

    marker_start = value_start
    if text.startswith("\r\n", marker_start):
        marker_start += 2
    elif marker_start < len(text) and text[marker_start] in "\r\n":
        marker_start += 1
    match = _PRIVATE_KEY_BEGIN.match(text, marker_start)
    if match is None:
        return None
    end_marker = f"-----END {match.group(1)}-----"
    marker_end = text.find(end_marker, match.end())
    if marker_end < 0:
        return len(text)
    return marker_end + len(end_marker)


def _parse_logged_value(text, key_end, key_metadata):
    """Return value content and suffix boundaries following a sensitive key."""

    normalized_key, quoted_key = key_metadata
    cursor = key_end
    while cursor < len(text) and text[cursor] in " \t":
        cursor += 1
    if cursor < len(text) and text[cursor] in ":=":
        cursor += 1
        while cursor < len(text) and text[cursor] in " \t":
            cursor += 1
    elif cursor == key_end or quoted_key is not None:
        return None
    if cursor >= len(text):
        return None

    is_private_key = normalized_key in {"privatekey", "sshprivatekey"}
    if is_private_key:
        block_end = _private_key_block_end(text, cursor)
        if block_end is not None:
            return cursor, block_end, block_end, "<redacted>"
    if text[cursor] in "\r\n":
        return None

    delimiter = _quote_delimiter_at(text, cursor)
    if delimiter is not None:
        slash_count, quote, content_start = delimiter
        closing = _find_quoted_end(text, content_start, slash_count, quote)
        if closing is None:
            if is_private_key and _private_key_block_end(text, content_start) is not None:
                return content_start, len(text), len(text), "<redacted>"
            line_end = len(text)
            for newline in ("\r", "\n"):
                newline_index = text.find(newline, content_start)
                if newline_index >= 0:
                    line_end = min(line_end, newline_index)
            return content_start, line_end, line_end, "<redacted>"
        content_end, after_value = closing
        return content_start, content_end, after_value, "<redacted>"

    value_end = cursor
    terminators = "\r\n,]}" if quoted_key is not None else "\r\n"
    while value_end < len(text) and text[value_end] not in terminators:
        value_end += 1
    if value_end == cursor:
        return None
    replacement = "<redacted>"
    if quoted_key is not None:
        slash_count, quote = quoted_key
        delimiter = "\\" * slash_count + quote
        replacement = f"{delimiter}<redacted>{delimiter}"
    return cursor, value_end, value_end, replacement


def _redact_logged_text(text):
    """Redact sensitive logged values without leaking escaped value suffixes."""

    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    if not text:
        return text

    source = str(text)
    fragments = []
    copied_until = 0
    cursor = 0
    while cursor < len(source):
        parsed_key = _parse_logged_key(source, cursor)
        if parsed_key is None:
            cursor += 1
            continue
        key_end, key_metadata = parsed_key
        parsed_value = _parse_logged_value(source, key_end, key_metadata)
        if parsed_value is None:
            cursor += 1
            continue
        value_start, value_end, after_value, replacement = parsed_value
        fragments.append(source[copied_until:value_start])
        fragments.append(replacement)
        fragments.append(source[value_end:after_value])
        copied_until = after_value
        cursor = after_value
    fragments.append(source[copied_until:])
    return "".join(fragments)


def _redact_subprocess_diagnostic(value):
    """Return a subprocess diagnostic copy with command and output redacted."""

    if isinstance(value, subprocess.CompletedProcess):
        args = value.args
        if isinstance(args, (list, tuple)):
            args = list(_redact_command_args(args))
        else:
            args = _redact_logged_text(args)
        return subprocess.CompletedProcess(
            args=args,
            returncode=value.returncode,
            stdout=_redact_logged_text(value.stdout),
            stderr=_redact_logged_text(value.stderr),
        )
    if isinstance(value, subprocess.TimeoutExpired):
        command = value.cmd
        if isinstance(command, (list, tuple)):
            command = list(_redact_command_args(command))
        else:
            command = _redact_logged_text(command)
        return subprocess.TimeoutExpired(
            command,
            value.timeout,
            output=_redact_logged_text(value.output),
            stderr=_redact_logged_text(value.stderr),
        )
    return value


def _sanitized_subprocess_exception(exc):
    """Return a fresh subprocess/OS exception containing only redacted state."""

    if isinstance(exc, subprocess.TimeoutExpired):
        return _redact_subprocess_diagnostic(exc)
    message = _redact_logged_text(str(exc))
    try:
        return type(exc)(message)
    except BaseException:  # uncommon exception constructors use a safe fallback
        return RuntimeError(f"AlphaGSM command execution failed: {message}")


def _capture_doctor_json(env, server_name, stage):
    """Persist best-effort JSON diagnostics without replacing a lifecycle failure."""
    directory = env.get("ALPHAGSM_DIAGNOSTICS_DIR")
    if not directory:
        return
    payload = {"schema_version": 1, "server": server_name, "stage": stage, "status": "unavailable"}
    try:
        result = run_alphagsm(env, server_name, "doctor", "--json", timeout=30)
        report = json.loads(_redact_logged_text(result.stdout))
        if not isinstance(report, dict) or report.get("schema_version") != 1:
            raise ValueError("Doctor returned an unsupported diagnostic schema")
        payload.update(report)
        payload["stage"] = stage
        payload["diagnostic_exit_code"] = result.returncode
    except Exception as exc:
        payload["diagnostic_error"] = _redact_logged_text(str(exc))
    try:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        prefix = re.sub(r"[^a-zA-Z0-9_.-]", "_", f"{server_name}-{stage}-")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", prefix=prefix,
                                         dir=target, encoding="utf-8", delete=False) as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
    except OSError as exc:
        print(_redact_logged_text(f"[diagnostic] Could not save doctor JSON: {exc}"))
    return payload


def run_alphagsm(env, *args, timeout=DEFAULT_TIMEOUT, capture_diagnostics=True):
    """Run the selected AlphaGSM CLI and return the CompletedProcess."""
    command = alphagsm_command(env) + list(args)
    working_dir = (
        Path(env["ALPHAGSM_CONFIG_LOCATION"]).resolve().parent
        if env.get("ALPHAGSM_BINARY") else REPO_ROOT
    )
    completed_result = None
    sanitized_error = None
    try:
        try:
            completed_result = subprocess.run(
                command,
                env=env,
                cwd=str(working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            sanitized_error = _sanitized_subprocess_exception(exc)
        if capture_diagnostics and (sanitized_error is not None or completed_result.returncode != 0) and len(args) >= 2 and args[1] not in {"doctor", "logs"}:
            _capture_doctor_json(env, args[0], args[1])
        if sanitized_error is not None:
            raise sanitized_error from None
        return completed_result
    finally:
        if sys.exc_info()[0] is not None:
            env = None
            args = _redact_command_args(args)
            command = list(_redact_command_args(command))
            completed_result = _redact_subprocess_diagnostic(completed_result)


def log_command_result(name, result, command_args=None, label=None):
    """Print a subprocess result for CI diagnostics."""
    del name
    del label
    del command_args
    print("\n=== alphagsm ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:")
        print(_redact_logged_text(result.stdout).rstrip())
    if result.stderr:
        print("stderr:")
        print(_redact_logged_text(result.stderr).rstrip())


def assert_alphagsm_result_ok(result):
    """Raise a redacted assertion when an AlphaGSM command fails."""

    if result.returncode == 0:
        return result
    result = _redact_subprocess_diagnostic(result)
    message = _redact_logged_text(result.stderr or result.stdout)
    if not message:
        message = f"AlphaGSM command failed with return code {result.returncode}"
    raise AssertionError(message)


def run_and_assert_ok(
    env,
    *args,
    timeout=DEFAULT_TIMEOUT,
    allow_known_steamcmd_skip=True,
):
    """Run alphagsm and assert a zero return code."""
    result = None
    command_failure = None
    try:
        result = run_alphagsm(env, *args, timeout=timeout)
        log_command_result("alphagsm", result, label="alphagsm")
        if result.returncode != 0:
            if allow_known_steamcmd_skip:
                skip_for_known_steamcmd_issue(result)
            try:
                assert_alphagsm_result_ok(result)
            except BaseException as exc:
                command_failure = exc
            if len(args) >= 2 and args[1] in {
                "start",
                "status",
                "query",
                "info",
                "stop",
                "restart",
            }:
                server_name = args[0]
                _run_readiness_diagnostic(
                    "Runtime",
                    lambda: _dump_alphagsm_runtime_logs(env, server_name),
                )
            if command_failure is not None:
                raise command_failure from None
        assert_alphagsm_result_ok(result)
        return _redact_subprocess_diagnostic(result)
    finally:
        if sys.exc_info()[0] is not None:
            env = None
            args = _redact_command_args(args)
            result = _redact_subprocess_diagnostic(result)


class _ReadinessRuntimeState:
    """Require consecutive trustworthy stopped reports before ending a wait."""

    def __init__(self):
        self.previous = None
        self.confirmations = 0
        self.last_diagnostic = ""

    @staticmethod
    def _stopped_identity(payload, server_name):
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            return None
        if payload.get("server", server_name) != server_name:
            return None
        runtime = payload.get("runtime")
        if not isinstance(runtime, dict) or runtime.get("running") is not False:
            return None
        if any(key.endswith("_error") and value for key, value in runtime.items()):
            return None
        backend = runtime.get("resolved_runtime")
        if backend == "docker":
            # running=False is also the doctor's initial value on daemon or
            # inspection failures. Only an inspected stopped container counts.
            if runtime.get("container_state") != "stopped":
                return None
            return backend, runtime.get("container_name", server_name)
        if backend == "process":
            return backend, server_name
        return None

    def poll(self, env, server_name, remaining_seconds):
        """Return true after two stopped snapshots; unknown evidence resets it."""
        identity = None
        try:
            result = run_alphagsm(env, server_name, "doctor", "--json",
                                  timeout=min(10, remaining_seconds))
            self.last_diagnostic = _redact_logged_text(
                f"returncode: {result.returncode}\n{result.stdout}\n{result.stderr}")
            if result.returncode == 0:
                identity = self._stopped_identity(json.loads(result.stdout), server_name)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            self.last_diagnostic = _redact_logged_text(str(exc))
        if identity is None:
            self.confirmations = 0
        else:
            self.confirmations = self.confirmations + 1 if identity == self.previous else 1
        self.previous = identity
        return self.confirmations >= 2

    def dump(self):
        """Keep the last sanitized liveness evidence alongside readiness logs."""
        if self.last_diagnostic:
            print("[diagnostic] Last readiness doctor --json poll:")
            print(self.last_diagnostic)


def wait_for_info_protocol(
    env,
    server_name,
    expected_protocol,
    timeout_seconds,
    expected_port=None,
):
    """Poll ``info --json`` until it returns the expected protocol and port."""

    if expected_port is not None:
        expected_port = int(expected_port)
    deadline = time.monotonic() + timeout_seconds
    last_result = None
    last_data = None
    runtime_state = _ReadinessRuntimeState()
    exited = False
    while True:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            break
        try:
            result = run_alphagsm(env, server_name, "info", "--json",
                                  timeout=min(30, remaining_seconds), capture_diagnostics=False)
        except subprocess.TimeoutExpired as exc:
            last_result = exc
        else:
            last_result = result
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    data = None
                else:
                    last_data = data
                    if isinstance(data, dict) and data.get("protocol") == expected_protocol and (
                        expected_port is None or data.get("port") == expected_port
                    ):
                        return data
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            break
        exited = runtime_state.poll(env, server_name, remaining_seconds)
        if exited:
            break
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            break
        time.sleep(min(5, remaining_seconds))

    failure_message = _redact_logged_text(
        f"info --json never returned protocol {expected_protocol!r} "
        f"within {timeout_seconds}s: last payload={last_data!r}"
    )
    if exited:
        failure_message = f"Server {server_name} exited before readiness (confirmed by two doctor --json polls)"
    diagnostic_result = _redact_subprocess_diagnostic(last_result)
    result = None
    last_result = None
    data = None
    last_data = None
    try:
        fail_readiness_timeout(
            env,
            server_name,
            failure_message,
            diagnostics=(
                (
                    "info --json",
                    lambda: _dump_runtime_log_poll(diagnostic_result, command="info --json"),
                ),
                ("Runtime state", runtime_state.dump),
            ),
        )
    finally:
        env = None
        diagnostic_result = None


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
            print(
                _redact_logged_text(
                    f"[diagnostic] Log file not found ({context}): {log_path}"
                )
            )
            return
        text = p.read_text(errors="replace")
        lines = text.splitlines()
        size = p.stat().st_size
        print(
            _redact_logged_text(
                f"[diagnostic] Log tail — {len(lines)} total lines, {size} bytes"
                + (f" [{context}]" if context else "")
                + f": {log_path}"
            )
        )
        shown = lines[-max_lines:]
        for line in shown:
            print(f"  {_redact_logged_text(line)}")
        if len(lines) > max_lines:
            print(f"  ... ({len(lines) - max_lines} earlier lines omitted)")
    except OSError as exc:
        print(
            _redact_logged_text(
                f"[diagnostic] Could not read log ({context}): {exc}"
            )
        )


def _dump_alphagsm_runtime_logs(env, server_name, lines=200):
    """Print AlphaGSM-managed console diagnostics for *server_name*."""

    report = _capture_doctor_json(env, server_name, "readiness")
    runtime = report.get("runtime", {}) if isinstance(report, dict) else {}
    if isinstance(runtime, dict) and runtime.get("resolved_runtime") == "docker" and runtime.get("container_name"):
        def dump_docker_processes():
            from tests.integration_tests.runtime_diagnostics import collect_docker_runtime_diagnostics

            for label, result in collect_docker_runtime_diagnostics(runtime["container_name"]):
                log_command_result("docker", result, label=label)

        _run_readiness_diagnostic("Docker processes", dump_docker_processes)
    for command_name, command_args in (
        ("logs", (server_name, "logs", "-n", str(lines))),
        ("doctor", (server_name, "doctor")),
    ):
        try:
            result = run_alphagsm(env, *command_args, timeout=120)
        except subprocess.TimeoutExpired as exc:
            print(
                f"[diagnostic] alphagsm command timed out after {exc.timeout}s"
            )
            continue
        log_command_result("alphagsm", result, label=f"alphagsm {command_name}")


def _run_readiness_diagnostic(label, diagnostic):
    """Run one redacted diagnostic without replacing a readiness failure."""

    try:
        diagnostic()
    except BaseException as exc:
        try:
            print(
                _redact_logged_text(
                    f"[diagnostic] {label} diagnostic collection failed: {exc}"
                )
            )
        except BaseException:
            pass


def fail_readiness_timeout(
    env,
    server_name,
    message,
    *,
    diagnostics=(),
):
    """Run best-effort diagnostics, then fail readiness with a redacted message."""

    message = _redact_logged_text(message)
    try:
        for label, diagnostic in diagnostics:
            _run_readiness_diagnostic(label, diagnostic)
        if env is not None and server_name is not None:
            _run_readiness_diagnostic(
                "Runtime",
                lambda: _dump_alphagsm_runtime_logs(env, server_name),
            )
        pytest.fail(message)
    finally:
        env = None
        server_name = None
        diagnostics = ()
        label = None
        diagnostic = None


def _report_suppressed_cleanup_error(stage, exc):
    """Best-effort report for cleanup errors hidden by a lifecycle failure."""

    try:
        print(
            _redact_logged_text(
                f"[diagnostic] AlphaGSM {stage} cleanup failed: {exc}"
            )
        )
    except BaseException:
        pass


def _sanitized_cleanup_exception(stage, exc):
    """Return a fresh cleanup exception that contains only redacted state."""

    if isinstance(exc, subprocess.TimeoutExpired):
        return _redact_subprocess_diagnostic(exc)
    message = _redact_logged_text(str(exc))
    try:
        return type(exc)(message)
    except BaseException:  # uncommon constructors use a safe fallback
        return RuntimeError(f"AlphaGSM {stage} cleanup failed: {message}")


def capture_alphagsm_stop(
    env,
    server_name,
    lifecycle_exception,
    timeout=DEFAULT_TIMEOUT,
):
    """Stop and log a server without replacing an active lifecycle failure."""

    stop_result = None
    standalone_error = None
    try:
        try:
            stop_result = run_alphagsm(env, server_name, "stop", timeout=timeout)
        except BaseException as exc:
            if lifecycle_exception is None:
                if isinstance(exc, _CONTROL_EXCEPTIONS):
                    raise
                standalone_error = _sanitized_cleanup_exception("stop", exc)
            else:
                _report_suppressed_cleanup_error("stop", exc)
                return None
        if standalone_error is not None:
            raise standalone_error from None

        try:
            log_command_result("alphagsm stop", stop_result)
        except BaseException as exc:
            if lifecycle_exception is None:
                if isinstance(exc, _CONTROL_EXCEPTIONS):
                    raise
                standalone_error = _sanitized_cleanup_exception("logging", exc)
            else:
                _report_suppressed_cleanup_error("logging", exc)
        if standalone_error is not None:
            raise standalone_error from None
        return _redact_subprocess_diagnostic(stop_result)
    finally:
        if sys.exc_info()[0] is not None or lifecycle_exception is not None:
            env = None
            lifecycle_exception = None
            stop_result = _redact_subprocess_diagnostic(stop_result)


# ---------------------------------------------------------------------------
# Wait helpers
# ---------------------------------------------------------------------------

_RUNTIME_LOG_MARKER_TAIL_LINES = 10_000


def _dump_runtime_log_poll(last_poll, command="logs"):
    """Print the last runtime-log readiness poll with redaction."""

    if isinstance(last_poll, subprocess.CompletedProcess):
        log_command_result(
            "alphagsm",
            last_poll,
            label=f"alphagsm {command} readiness poll",
        )
    elif isinstance(last_poll, subprocess.TimeoutExpired):
        print(
            f"[diagnostic] Last alphagsm {command} readiness poll timed out after "
            f"{last_poll.timeout}s"
        )
        if last_poll.stdout:
            print(_redact_logged_text(last_poll.stdout).rstrip())
        if last_poll.stderr:
            print(_redact_logged_text(last_poll.stderr).rstrip())
    else:
        print(f"[diagnostic] No alphagsm {command} readiness poll completed")


def _dump_glob_log_timeout(log_dir_path, glob_pattern, markers):
    """Print redacted tails for a failed glob-log readiness wait."""

    if log_dir_path.exists():
        matched = list(log_dir_path.glob(glob_pattern))
        if matched:
            for log_path in matched:
                _dump_log(
                    log_path,
                    context=f"glob timeout, looking for {markers!r}",
                )
        else:
            print(
                _redact_logged_text(
                    f"[diagnostic] No files matching {glob_pattern!r} "
                    f"in {log_dir_path}"
                )
            )
    else:
        print(_redact_logged_text(f"[diagnostic] Log dir not found: {log_dir_path}"))


def _print_readiness_diagnostic(message):
    """Print a redacted readiness diagnostic summary."""

    print(_redact_logged_text(message))


def _dump_a2s_tcp_probe(host, port):
    """Probe and report the TCP side of an A2S readiness timeout."""

    try:
        with socket.create_connection((host, port), timeout=5):
            tcp_diagnostic = f"TCP port {host}:{port} is open"
    except OSError as exc:
        tcp_diagnostic = f"TCP probe on {host}:{port} failed: {exc}"
    _print_readiness_diagnostic(f"[diagnostic] {tcp_diagnostic}")


def wait_for_runtime_log_marker(env, server_name, markers, timeout_seconds):
    """Poll AlphaGSM-managed runtime logs until one of *markers* appears."""

    deadline = time.monotonic() + timeout_seconds
    last_poll = None
    runtime_state = _ReadinessRuntimeState()
    exited = False
    while True:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            break
        poll_timeout = min(120, remaining_seconds)
        try:
            result = run_alphagsm(
                env,
                server_name,
                "logs",
                "-n",
                str(_RUNTIME_LOG_MARKER_TAIL_LINES),
                timeout=poll_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            last_poll = exc
        else:
            last_poll = result
            collected = "\n".join(
                text for text in (result.stdout, result.stderr) if text
            )
            if result.returncode == 0 and any(
                marker in collected for marker in markers
            ):
                return _redact_logged_text(collected)
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            break
        exited = runtime_state.poll(env, server_name, remaining_seconds)
        if exited:
            break
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            break
        time.sleep(min(2, remaining_seconds))

    diagnostic_poll = _redact_subprocess_diagnostic(last_poll)
    result = None
    last_poll = None
    collected = None
    failure_message = (f"Server {server_name} exited before readiness (confirmed by two doctor --json polls)"
                       if exited else f"Runtime logs never showed readiness markers {markers!r} "
                       f"within {timeout_seconds}s for {server_name}")
    try:
        fail_readiness_timeout(
            env,
            server_name,
            failure_message,
            diagnostics=(
                (
                    "Last runtime-log poll",
                    lambda: _dump_runtime_log_poll(diagnostic_poll),
                ),
                ("Runtime state", runtime_state.dump),
            ),
        )
    finally:
        env = None
        markers = None
        diagnostic_poll = None


def wait_for_log_marker(log_path, markers, timeout_seconds, env=None, server_name=None):
    """Poll a log file until one of *markers* appears; return the log text.

    On timeout dumps the full log tail to captured stdout and raises a test
    FAILURE so the problem is visible and must be fixed.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            log_text = log_path.read_text(errors="replace")
            if any(marker in log_text for marker in markers):
                return _redact_logged_text(log_text)
        time.sleep(2)
    log_text = None
    try:
        fail_readiness_timeout(
            env,
            server_name,
            f"Log never showed readiness markers {markers!r} within {timeout_seconds}s: "
            f"{log_path}",
            diagnostics=(
                (
                    "Local log",
                    lambda: _dump_log(
                        log_path,
                        context=f"looking for {markers!r}",
                    ),
                ),
            ),
        )
    finally:
        env = None
        markers = None
        log_path = None


def wait_for_glob_log_marker(
    log_dir,
    glob_pattern,
    markers,
    timeout_seconds,
    env=None,
    server_name=None,
):
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
                        return _redact_logged_text(text)
                except OSError:
                    pass
        time.sleep(2)
    text = None
    try:
        fail_readiness_timeout(
            env,
            server_name,
            f"Log never showed readiness markers {markers!r} within {timeout_seconds}s "
            f"in {log_dir}",
            diagnostics=(
                (
                    "Glob log",
                    lambda: _dump_glob_log_timeout(
                        log_dir_path,
                        glob_pattern,
                        markers,
                    ),
                ),
            ),
        )
    finally:
        env = None
        markers = None
        log_dir = None
        log_dir_path = None


def wait_for_tcp_closed(host, port, timeout_seconds):
    """Wait until TCP connects fail on every relevant runtime endpoint."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        endpoint_open = False
        for probe_host in _runtime_probe_hosts(host):
            try:
                with socket.create_connection((probe_host, port), timeout=2):
                    endpoint_open = True
            except Exception:  # noqa: BLE001
                continue
        if not endpoint_open:
            return
        time.sleep(2)
    raise AssertionError(f"TCP port {host}:{port} still open after {timeout_seconds}s")


def wait_for_udp_closed(host, port, timeout_seconds):
    """Wait until UDP Source queries stop responding on every endpoint."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        endpoint_open = False
        for probe_host in _runtime_probe_hosts(host):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2)
                try:
                    sock.sendto(
                        b"\xFF\xFF\xFF\xFFTSource Engine Query\x00",
                        (probe_host, port),
                    )
                    sock.recv(4096)
                    endpoint_open = True
                except Exception:  # noqa: BLE001
                    continue
        if not endpoint_open:
            return
        time.sleep(2)
    raise AssertionError(f"UDP port {host}:{port} still responds after {timeout_seconds}s")


def wait_for_generic_udp_closed(host, port, timeout_seconds, payload=b"\x00"):
    """Wait until generic UDP traffic fails on every relevant endpoint."""

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        endpoint_open = False
        for probe_host in _runtime_probe_hosts(host):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(2)
                    sock.connect((probe_host, int(port)))
                    sock.send(payload)
                    try:
                        sock.recv(1)
                    except socket.timeout:
                        pass
                    endpoint_open = True
            except OSError:
                continue
        if not endpoint_open:
            return
        time.sleep(2)
    raise AssertionError(
        f"UDP port {host}:{port} still accepts traffic after {timeout_seconds}s"
    )

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
        for probe_host in _runtime_probe_hosts(host):
            try:
                query_utils.a2s_info(
                    probe_host,
                    port,
                    timeout=_A2S_PHASE1_TIMEOUT,
                    phase2_timeout=_A2S_PHASE2_TIMEOUT,
                )
                return
            except query_utils.QueryError as exc:
                last_exc = exc
        # No additional sleep: Phase 1 already waits 15 s on timeout; Phase 2
        # (when it runs) takes up to 120 s, providing a natural gap.

    last_error = _redact_logged_text(str(last_exc))
    last_exc = None
    diagnostic_summary = (
        f"[diagnostic] A2S on {host}:{port} never responded within {timeout_seconds}s"
        f" — last error: {last_error}"
    )
    tcp_check_port = tcp_port if tcp_port is not None else port
    diagnostics = [
        (
            "A2S summary",
            lambda: _print_readiness_diagnostic(diagnostic_summary),
        ),
        (
            "A2S TCP probe",
            lambda: _dump_a2s_tcp_probe(host, tcp_check_port),
        ),
    ]
    if log_path is not None:
        diagnostics.append(
            (
                "Local log",
                lambda: _dump_log(
                    log_path,
                    context=f"A2S timeout on port {port}",
                ),
            )
        )
    fail_readiness_timeout(
        None,
        None,
        f"A2S on {host}:{port} never responded within {timeout_seconds}s: "
        f"{last_error}",
        diagnostics=tuple(diagnostics),
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
        for probe_host in _runtime_probe_hosts(host):
            try:
                with _socket.create_connection((probe_host, port), timeout=2):
                    return
            except OSError as exc:
                last_exc = exc
        time.sleep(2)
    last_error = _redact_logged_text(str(last_exc))
    last_exc = None
    diagnostic_summary = (
        f"[diagnostic] TCP port {host}:{port} never opened within {timeout_seconds}s"
        f" — last error: {last_error}"
    )
    diagnostics = [
        (
            "TCP summary",
            lambda: _print_readiness_diagnostic(diagnostic_summary),
        )
    ]
    if log_path is not None:
        diagnostics.append(
            (
                "Local log",
                lambda: _dump_log(
                    log_path,
                    context=f"TCP open timeout on port {port}",
                ),
            )
        )
    fail_readiness_timeout(
        None,
        None,
        f"TCP port {host}:{port} never opened within {timeout_seconds}s",
        diagnostics=tuple(diagnostics),
    )


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
        for probe_host in _runtime_probe_hosts(host):
            try:
                query_utils.udp_ping(probe_host, port)
                return
            except query_utils.QueryError as exc:
                last_exc = exc
        time.sleep(2)
    last_error = _redact_logged_text(str(last_exc))
    last_exc = None
    diagnostic_summary = (
        f"[diagnostic] UDP port {host}:{port} never opened within {timeout_seconds}s"
        f" — last error: {last_error}"
    )
    diagnostics = [
        (
            "UDP summary",
            lambda: _print_readiness_diagnostic(diagnostic_summary),
        )
    ]
    if log_path is not None:
        diagnostics.append(
            (
                "Local log",
                lambda: _dump_log(
                    log_path,
                    context=f"UDP open timeout on port {port}",
                ),
            )
        )
    fail_readiness_timeout(
        None,
        None,
        f"UDP port {host}:{port} never opened within {timeout_seconds}s",
        diagnostics=tuple(diagnostics),
    )


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
        for probe_host in _runtime_probe_hosts(host):
            try:
                query_utils.quake_status(
                    probe_host,
                    port,
                    timeout=_QUAKE_SOCKET_TIMEOUT,
                )
                return
            except query_utils.QueryError as exc:
                last_exc = exc
        time.sleep(2)
    last_error = _redact_logged_text(str(last_exc))
    last_exc = None
    diagnostic_summary = (
        f"[diagnostic] Quake status on {host}:{port} never responded within {timeout_seconds}s"
        f" — last error: {last_error}"
    )
    diagnostics = [
        (
            "Quake summary",
            lambda: _print_readiness_diagnostic(diagnostic_summary),
        )
    ]
    if log_path is not None:
        diagnostics.append(
            (
                "Local log",
                lambda: _dump_log(
                    log_path,
                    context=f"Quake timeout on port {port}",
                ),
            )
        )
    fail_readiness_timeout(
        None,
        None,
        f"Quake status on {host}:{port} never responded within {timeout_seconds}s: "
        f"{last_error}",
        diagnostics=tuple(diagnostics),
    )


def wait_for_quakeworld_ready(host, port, timeout_seconds, log_path=None):
    """Poll QuakeWorld UDP ``status`` on *host*:*port* until the server responds."""

    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from utils import query as query_utils  # pylint: disable=import-outside-toplevel
    deadline = time.time() + timeout_seconds
    last_exc = None
    _QUAKEWORLD_SOCKET_TIMEOUT = 10.0
    while time.time() < deadline:
        for probe_host in _runtime_probe_hosts(host):
            try:
                query_utils.quakeworld_status(
                    probe_host,
                    port,
                    timeout=_QUAKEWORLD_SOCKET_TIMEOUT,
                )
                return
            except query_utils.QueryError as exc:
                last_exc = exc
        time.sleep(2)
    last_error = _redact_logged_text(str(last_exc))
    last_exc = None
    diagnostic_summary = (
        f"[diagnostic] QuakeWorld status on {host}:{port} never responded within {timeout_seconds}s"
        f" — last error: {last_error}"
    )
    diagnostics = [
        (
            "QuakeWorld summary",
            lambda: _print_readiness_diagnostic(diagnostic_summary),
        )
    ]
    if log_path is not None:
        diagnostics.append(
            (
                "Local log",
                lambda: _dump_log(
                    log_path,
                    context=f"QuakeWorld timeout on port {port}",
                ),
            )
        )
    fail_readiness_timeout(
        None,
        None,
        f"QuakeWorld status on {host}:{port} never responded within {timeout_seconds}s: "
        f"{last_error}",
        diagnostics=tuple(diagnostics),
    )


def wait_for_quake2_ready(host, port, timeout_seconds, log_path=None):
    """Poll Quake II UDP ``status`` until the server responds."""

    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from utils import query as query_utils  # pylint: disable=import-outside-toplevel
    deadline = time.time() + timeout_seconds
    last_exc = None
    _QUAKE_SOCKET_TIMEOUT = 10.0
    while time.time() < deadline:
        for probe_host in _runtime_probe_hosts(host):
            try:
                query_utils.quake2_status(
                    probe_host,
                    port,
                    timeout=_QUAKE_SOCKET_TIMEOUT,
                )
                return
            except query_utils.QueryError as exc:
                last_exc = exc
        time.sleep(2)
    last_error = _redact_logged_text(str(last_exc))
    last_exc = None
    diagnostic_summary = (
        f"[diagnostic] Quake II status on {host}:{port} never responded within {timeout_seconds}s"
        f" — last error: {last_error}"
    )
    diagnostics = [
        (
            "Quake II summary",
            lambda: _print_readiness_diagnostic(diagnostic_summary),
        )
    ]
    if log_path is not None:
        diagnostics.append(
            (
                "Local log",
                lambda: _dump_log(
                    log_path,
                    context=f"Quake II timeout on port {port}",
                ),
            )
        )
    fail_readiness_timeout(
        None,
        None,
        f"Quake II status on {host}:{port} never responded within {timeout_seconds}s: "
        f"{last_error}",
        diagnostics=tuple(diagnostics),
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

    if _steamcmd_state_202_flake(combined, app_id):
        extra = f" (app {app_id})" if app_id else ""
        snippet = _redact_logged_text(combined[:300]).replace("\n", " | ")
        reason = (
            f"SteamCMD flake skip — repeated known state 0x202 during setup"
            f"{extra}: {snippet}"
        )
        result = None
        combined = None
        pytest.skip(reason)

    # Only markers that make it impossible to run the test in CI at all
    # (authentication required, or module intentionally disabled) warrant a
    # skip.  Download/install failures should be visible as test failures.
    skip_markers = (
        "No subscription",
        "SteamCMD username required for this server",
        "is currently disabled",
        "ENABLED (BYO):",
        "ENABLED (AUTH):",
    )
    for marker in skip_markers:
        if marker in combined:
            extra = f" (app {app_id})" if app_id else ""
            snippet = _redact_logged_text(combined[:300]).replace("\n", " | ")
            reason = (
                f"Setup skipped — {marker!r} in output{extra}: {snippet}"
            )
            result = None
            combined = None
            pytest.skip(reason)
