"""Optional Linux user service for the foreground Sector Alpha agent.

Enrollment, reporting and management stay independent of this unit. Installing
it only keeps `alphagsm agent run` alive for the current operator.
"""

import os
import shutil
import subprocess
from pathlib import Path

from utils.platform_info import PLATFORM


UNIT_NAME = "alphagsm-agent.service"
_UNSUPPORTED = (
    "Linux systemd is the supported optional agent service. "
    "On this platform, run alphagsm agent run in the foreground or install it with your own service manager."
)


class ServiceInstallError(ValueError):
    """The optional user service could not be installed or removed."""


def install_hint(*, platform=None, which=None, home=None, env=None):
    """Tell the operator how to keep the agent running, without installing it."""
    if (PLATFORM if platform is None else platform) != "linux":
        return "Keep alphagsm agent run in the foreground."
    finder = shutil.which if which is None else which
    if finder("systemctl") is None:
        return (
            "Keep alphagsm agent run in the foreground, or install that command with your own service manager."
        )
    if unit_file(home, env).is_file():
        return "Restart the installed agent service with: alphagsm agent install-service"
    return "To keep the agent running after you close the terminal: alphagsm agent install-service"


def install(executable=None, *, runner=None, home=None, env=None, platform=None, user=None, which=None):
    """Write and start a user service that runs this AlphaGSM program."""
    _require_linux(platform)
    finder = shutil.which if which is None else which
    if finder("systemctl") is None:
        raise ServiceInstallError(
            "systemctl is not available for this user. "
            "Run alphagsm agent run in the foreground, or install it with your own service manager."
        )
    program = resolve_executable(executable)
    selected_env = os.environ if env is None else env
    text = render_unit(program, selected_env.get("ALPHAGSM_CONFIG_LOCATION"))
    path = unit_file(home, selected_env)
    _write_unit(path, text)
    invoke = _default_runner if runner is None else runner
    _systemctl(invoke, "daemon-reload")
    _systemctl(invoke, "enable", UNIT_NAME)
    _systemctl(invoke, "restart", UNIT_NAME)
    print("Installed " + UNIT_NAME + " and started it.")
    print("It runs: " + program + " agent run")
    print("Reporting and management are unchanged.")
    linger = _linger_line(invoke, _user_name(user))
    if linger:
        print(linger)


def uninstall(*, runner=None, home=None, env=None, platform=None, which=None):
    """Remove the user service. Local enrollment and permissions stay in place."""
    _require_linux(platform)
    finder = shutil.which if which is None else which
    if finder("systemctl") is None:
        raise ServiceInstallError("systemctl is not available, so the agent service unit was left unchanged.")
    path = unit_file(home, os.environ if env is None else env)
    if path.is_symlink():
        raise ServiceInstallError("Refusing to remove the agent service through a symlink")
    if not path.is_file():
        print("No AlphaGSM agent user service is installed.")
        return
    invoke = _default_runner if runner is None else runner
    result = invoke(["systemctl", "--user", "disable", "--now", UNIT_NAME])
    if result.returncode != 0 and not _unit_absent(result):
        detail = (result.stderr or result.stdout or "").strip()
        raise ServiceInstallError(
            "systemctl --user disable --now " + UNIT_NAME + " failed" + (": " + detail if detail else "")
        )
    path.unlink()
    _systemctl(invoke, "daemon-reload")
    print("Removed the AlphaGSM agent user service. Local enrollment and permissions are unchanged.")


def resolve_executable(invoked):
    """Absolute program path the service will execute."""
    import sys

    if getattr(sys, "frozen", False):
        candidate = sys.executable
    elif invoked:
        candidate = invoked if os.path.isabs(invoked) else os.path.abspath(invoked)
        if not os.path.isfile(candidate):
            found = shutil.which(invoked)
            if found:
                candidate = found
    else:
        here = os.path.abspath(__file__)
        candidate = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(here))), "alphagsm")
    if candidate and any(ord(char) < 32 for char in candidate):
        raise ServiceInstallError("The AlphaGSM program path contains unsupported characters")
    if not candidate or not os.path.isabs(candidate) or not os.path.isfile(candidate):
        raise ServiceInstallError("Install the service from the AlphaGSM program you want it to run")
    if not os.access(candidate, os.X_OK):
        raise ServiceInstallError("The AlphaGSM program must be an executable file")
    return candidate


def render_unit(executable, config_location=None):
    """systemd user unit. It never enables reporting or management."""
    lines = [
        "[Unit]",
        "Description=AlphaGSM Sector Alpha agent",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Service]",
        "Type=simple",
        "ExecStart=" + systemd_quote(executable) + " agent run",
    ]
    if config_location:
        if any(ord(char) < 32 for char in config_location):
            raise ServiceInstallError("The AlphaGSM config location cannot be stored in the service")
        lines.append("Environment=ALPHAGSM_CONFIG_LOCATION=" + systemd_quote(config_location))
    lines.extend([
        "Restart=on-failure",
        "RestartSec=5",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])
    return "\n".join(lines)


def systemd_quote(value):
    """Quote one systemd word, including specifier escapes."""
    escaped = value.replace("\\", "\\\\").replace("%", "%%").replace('"', '\\"')
    return '"' + escaped + '"'


def unit_file(home=None, env=None):
    """Path of the managed user unit."""
    selected = os.environ if env is None else env
    base = selected.get("XDG_CONFIG_HOME")
    if not base:
        base = str((Path.home() if home is None else Path(home)) / ".config")
    return Path(base) / "systemd" / "user" / UNIT_NAME


def _require_linux(platform):
    if (PLATFORM if platform is None else platform) != "linux":
        raise ServiceInstallError(_UNSUPPORTED)


def _user_name(user):
    if user:
        return user
    return os.environ.get("USER") or ""


def _default_runner(args):
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _systemctl(runner, *args):
    result = runner(["systemctl", "--user", *args])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        rendered = " ".join(args)
        raise ServiceInstallError("systemctl --user " + rendered + " failed" + (": " + detail if detail else ""))
    return result


def _unit_absent(result):
    text = ((result.stderr or "") + "\n" + (result.stdout or "")).lower()
    return any(phrase in text for phrase in ("not found", "does not exist", "not loaded"))


def _write_unit(path, text):
    if path.is_symlink() or path.parent.is_symlink():
        raise ServiceInstallError("Refusing to write the agent service through a symlink")
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    except OSError as exc:
        raise ServiceInstallError("Could not create the systemd user directory: " + str(exc)) from exc
    if path.is_symlink() or path.parent.is_symlink():
        raise ServiceInstallError("Refusing to write the agent service through a symlink")
    temporary = path.with_name("." + path.name + ".tmp")
    if temporary.is_symlink():
        raise ServiceInstallError("Refusing to write the agent service through a symlink")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except OSError as exc:
        raise ServiceInstallError("Could not write the agent service unit: " + str(exc)) from exc


def _linger_line(runner, user):
    if not user:
        return ""
    try:
        result = runner(["loginctl", "show-user", user, "-p", "Linger"])
    except OSError:
        return ""
    if result.returncode != 0 or "Linger=no" not in (result.stdout or ""):
        return ""
    return "This service stops when you log out. To keep it running, enable lingering: loginctl enable-linger"
