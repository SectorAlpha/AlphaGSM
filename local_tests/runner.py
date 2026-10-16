"""Run AlphaGSM commands for local auth and BYO tests without recording secrets."""

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_ENV_MARKERS = ("PASSWORD", "SECRET", "STEAM_GUARD", "SSFN")
SECRET_TEXT = re.compile(r"(?i)(password|steam guard|sentry|ssfn[0-9]|config\.vdf)")


def server_name(module_name):
    """Return a short alphanumeric AlphaGSM server name."""

    compact = re.sub(r"[^A-Za-z0-9]", "", module_name).lower()
    return ("la" + compact)[:24] or "lalocal"


def free_port():
    """Ask the kernel for an unused UDP port."""

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def redact(text, extras=()):
    """Remove secret-shaped text before a failure is stored or printed."""

    redacted = text or ""
    for extra in extras:
        if extra:
            redacted = redacted.replace(str(extra), "<redacted>")
    return SECRET_TEXT.sub("<redacted>", redacted)


def child_env(config_path):
    """Return an environment that cannot carry passwords into SteamCMD."""

    env = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in SECRET_ENV_MARKERS)
    }
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env.pop("PYTHONHOME", None)
    return env


def alphagsm_command(env):
    """Use a standalone binary when the operator supplied one."""

    binary = env.get("ALPHAGSM_BINARY")
    if binary:
        return [str(Path(binary).expanduser())]
    return [sys.executable, str(REPO_ROOT / "alphagsm")]


def run_alphagsm(env, *args, timeout=120):
    """Run one AlphaGSM command and return its completed process."""

    completed = subprocess.run(
        alphagsm_command(env) + list(args),
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    completed.stdout = redact(completed.stdout)
    completed.stderr = redact(completed.stderr)
    return completed


def assert_ok(completed, action):
    """Fail with redacted command output."""

    if completed.returncode == 0:
        return
    raise AssertionError(
        "%s failed with code %s\n%s\n%s" % (
            action,
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
    )


def write_config(config_path, home_dir, state_dir):
    """Write a disposable config. The profile directory is only referenced."""

    download_root = home_dir / "downloads"
    lines = [
        "[core]",
        "alphagsm_path = %s" % state_dir,
        "userconf = %s" % home_dir,
        "",
        "[downloader]",
        "db_path = %s" % (download_root / "downloads.txt"),
        "target_path = %s" % (download_root / "downloads"),
        "",
        "[server]",
        "datapath = %s" % (home_dir / "conf"),
        "servermodulespackage = gamemodules.",
        "",
        "[runtime]",
        "backend = %s" % os.environ.get("ALPHAGSM_LOCAL_RUNTIME", "process"),
        "",
        "[process]",
        "backend = screen",
        "",
        "[docker]",
        "backend = subprocess",
        "",
        "[screen]",
        "screenlog_path = %s" % (home_dir / "logs"),
        "sessiontag = AlphaGSM-LocalAuth#",
        "keeplogs = 1",
        "",
    ]
    config_path.write_text("\n".join(lines), encoding="utf-8")


def _json_object(text):
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise AssertionError("info --json did not print an object:\n" + text)
    return json.loads(text[start:end + 1])


def _reject_secret_fields(value):
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if "password" in lowered or lowered in {"token", "secret", "guard"}:
                raise AssertionError("info JSON contained a secret field")
            _reject_secret_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_secret_fields(item)


def wait_for_query(env, name, timeout):
    """Poll the module's own query command until it reports a response."""

    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        completed = run_alphagsm(env, name, "query", timeout=60)
        last = completed.stdout + completed.stderr
        if completed.returncode == 0 and "Server is responding" in completed.stdout:
            return completed
        time.sleep(3)
    raise AssertionError("Query did not respond:\n" + last)


def lifecycle(module_name, *, profile, assets, state_dir, work_dir, ready_timeout):
    """Create, set up, query, and stop one server through AlphaGSM commands."""

    home_dir = Path(work_dir) / server_name(module_name)
    install_dir = home_dir / "server"
    config_path = home_dir / "alphagsm.conf"
    home_dir.mkdir(parents=True, exist_ok=True)
    write_config(config_path, home_dir, state_dir)
    env = child_env(config_path)
    name = server_name(module_name)
    port = free_port()
    setup = [name, "setup", "-n", str(port), str(install_dir)]
    if profile and assets:
        raise AssertionError("Pass either a Steam auth profile or an assets directory")
    if profile:
        setup.extend(["--auth-profile", profile])
    if assets:
        setup.extend(["--assets", str(assets)])

    assert_ok(run_alphagsm(env, name, "create", module_name, timeout=120), "create")
    try:
        assert_ok(run_alphagsm(env, *setup, timeout=3600), "setup")
        assert_ok(run_alphagsm(env, name, "start", timeout=180), "start")
        wait_for_query(env, name, ready_timeout)
        info = run_alphagsm(env, name, "info", timeout=60)
        assert_ok(info, "info")
        info_json = run_alphagsm(env, name, "info", "--json", timeout=60)
        assert_ok(info_json, "info --json")
        payload = _json_object(info_json.stdout)
        assert any(key in payload for key in ("name", "map", "players", "max_players", "protocol"))
        _reject_secret_fields(payload)
    finally:
        run_alphagsm(env, name, "stop", timeout=180)
    status = run_alphagsm(env, name, "status", timeout=60)
    assert_ok(status, "status")
    if "isn't running" not in status.stdout:
        raise AssertionError("Server was still running after stop:\n" + status.stdout)
