"""Optional Linux service for the Sector Alpha agent.

AlphaGSM runs the agent. There is no separate alphagsm-agent program.
`install-service` keeps `alphagsm agent run` alive for this user.
`install-service --system` installs that same command as a system service
for one operator account. Enrollment, reporting and management stay unchanged.
"""

import grp
import os
import pwd
import shutil
import subprocess
from collections import namedtuple
from pathlib import Path

from utils.platform_info import PLATFORM


UNIT_NAME = "alphagsm.service"
SYSTEM_UNIT_DIR = "/etc/systemd/system"
Account = namedtuple("Account", ("name", "group", "home"))
_UNSUPPORTED = (
    "Linux systemd is the supported optional agent service. "
    "On this platform, run alphagsm agent run in the foreground or install it with your own service manager."
)


class ServiceInstallError(ValueError):
    """The optional agent service could not be installed or removed."""


def install_hint(*, platform=None, which=None, home=None, env=None, system_dir=None):
    """Tell the operator how to keep the agent running, without installing it."""
    if (PLATFORM if platform is None else platform) != "linux":
        return "Keep alphagsm agent run in the foreground."
    finder = shutil.which if which is None else which
    if finder("systemctl") is None:
        return (
            "Keep alphagsm agent run in the foreground, or install that command with your own service manager."
        )
    if system_unit_file(system_dir).is_file():
        return "Restart the system service with: alphagsm agent install-service --system"
    if unit_file(home, env).is_file():
        return "Restart the installed service with: alphagsm agent install-service"
    return (
        "To keep the agent running after you close the terminal: alphagsm agent install-service. "
        "For a system service: alphagsm agent install-service --system"
    )


def install(
    executable=None,
    *,
    runner=None,
    home=None,
    env=None,
    platform=None,
    user=None,
    which=None,
    system=False,
    account=None,
    system_dir=None,
):
    """Install and start the user service, or a system service with --system."""
    _require_linux(platform)
    finder = shutil.which if which is None else which
    if finder("systemctl") is None:
        raise ServiceInstallError(
            "systemctl is not available for this user. "
            "Run alphagsm agent run in the foreground, or install it with your own service manager."
        )
    program = resolve_executable(executable)
    selected_env = os.environ if env is None else env
    invoke = _default_runner if runner is None else runner
    if system:
        selected = account if account is not None else lookup_account(user)
        text = render_unit(program, selected_env.get("ALPHAGSM_CONFIG_LOCATION"), account=selected)
        path = system_unit_file(system_dir)
        _reject_user_unit(home, selected_env)
        _require_system_write(path)
        _write_unit(path, text)
        _systemctl(invoke, "daemon-reload", system=True)
        _systemctl(invoke, "enable", UNIT_NAME, system=True)
        _systemctl(invoke, "restart", UNIT_NAME, system=True)
        print("Installed the system service " + UNIT_NAME + " and started it.")
        print("It runs as " + selected.name + ": " + program + " agent run")
        print("Reporting and management are unchanged.")
        return
    _reject_system_unit(system_dir)
    text = render_unit(program, selected_env.get("ALPHAGSM_CONFIG_LOCATION"))
    path = unit_file(home, selected_env)
    _write_unit(path, text)
    _systemctl(invoke, "daemon-reload")
    _systemctl(invoke, "enable", UNIT_NAME)
    _systemctl(invoke, "restart", UNIT_NAME)
    print("Installed the user service " + UNIT_NAME + " and started it.")
    print("It runs: " + program + " agent run")
    print("Reporting and management are unchanged.")
    linger = _linger_line(invoke, _user_name(user))
    if linger:
        print(linger)


def uninstall(*, runner=None, home=None, env=None, platform=None, which=None, system=False, system_dir=None):
    """Remove the selected service. Local enrollment and permissions stay in place."""
    _require_linux(platform)
    finder = shutil.which if which is None else which
    if finder("systemctl") is None:
        raise ServiceInstallError("systemctl is not available, so the agent service unit was left unchanged.")
    path = system_unit_file(system_dir) if system else unit_file(home, os.environ if env is None else env)
    if path.is_symlink():
        raise ServiceInstallError("Refusing to remove the agent service through a symlink")
    label = "system" if system else "user"
    if not path.is_file():
        print("No AlphaGSM " + label + " service is installed.")
        return
    if system:
        _require_system_write(path)
    invoke = _default_runner if runner is None else runner
    result = invoke(_systemctl_command("disable", "--now", UNIT_NAME, system=system))
    if result.returncode != 0 and not _unit_absent(result):
        detail = (result.stderr or result.stdout or "").strip()
        rendered = " ".join(_systemctl_command("disable", "--now", UNIT_NAME, system=system))
        raise ServiceInstallError(rendered + " failed" + (": " + detail if detail else ""))
    path.unlink()
    _systemctl(invoke, "daemon-reload", system=system)
    print("Removed the AlphaGSM " + label + " service. Local enrollment and permissions are unchanged.")


def lookup_account(user):
    """Operator account for a system service. The service does not run as root."""
    name = user or os.environ.get("SUDO_USER") or os.environ.get("USER") or ""
    if name == "root":
        raise ServiceInstallError(
            "The system service does not run as root. Choose the operator with --service-user."
        )
    _plain_name(name, "account")
    try:
        record = pwd.getpwnam(name)
    except KeyError as exc:
        raise ServiceInstallError("Unknown service account: " + name) from exc
    if not record.pw_dir or record.pw_dir == "/":
        raise ServiceInstallError("The service account needs a home directory")
    group = grp.getgrgid(record.pw_gid).gr_name
    _plain_name(group, "group")
    if any(ord(char) < 32 for char in record.pw_dir):
        raise ServiceInstallError("The service home directory contains unsupported characters")
    return Account(name, group, record.pw_dir)


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


def render_unit(executable, config_location=None, *, account=None):
    """systemd unit. It runs alphagsm agent run and never changes consent."""
    lines = [
        "[Unit]",
        "Description=AlphaGSM Sector Alpha agent",
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Service]",
        "Type=simple",
    ]
    if account is not None:
        _plain_name(account.name, "account")
        _plain_name(account.group, "group")
        if any(ord(char) < 32 for char in account.home):
            raise ServiceInstallError("The service home directory contains unsupported characters")
        lines.append("User=" + account.name)
        lines.append("Group=" + account.group)
    lines.append("ExecStart=" + systemd_quote(executable) + " agent run")
    if account is not None:
        lines.append("Environment=HOME=" + systemd_quote(account.home))
        lines.append("Environment=USER=" + systemd_quote(account.name))
    if config_location:
        if any(ord(char) < 32 for char in config_location):
            raise ServiceInstallError("The AlphaGSM config location cannot be stored in the service")
        lines.append("Environment=ALPHAGSM_CONFIG_LOCATION=" + systemd_quote(config_location))
    lines.extend([
        "Restart=on-failure",
        "RestartSec=5",
        "",
        "[Install]",
        "WantedBy=" + ("multi-user.target" if account is not None else "default.target"),
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


def system_unit_file(directory=None):
    """Path of the managed system unit."""
    return Path(SYSTEM_UNIT_DIR if directory is None else directory) / UNIT_NAME


def _plain_name(value, label):
    if not isinstance(value, str) or not value or any(ord(char) < 32 or char in " \"%\\" for char in value):
        raise ServiceInstallError("The service " + label + " contains unsupported characters")


def _require_linux(platform):
    if (PLATFORM if platform is None else platform) != "linux":
        raise ServiceInstallError(_UNSUPPORTED)


def _user_name(user):
    if user:
        return user
    return os.environ.get("USER") or ""


def _default_runner(args):
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _systemctl_command(*args, system=False):
    if system:
        return ["systemctl", *args]
    return ["systemctl", "--user", *args]


def _systemctl(runner, *args, system=False):
    command = _systemctl_command(*args, system=system)
    result = runner(command)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ServiceInstallError(" ".join(command) + " failed" + (": " + detail if detail else ""))
    return result


def _unit_absent(result):
    text = ((result.stderr or "") + "\n" + (result.stdout or "")).lower()
    return any(phrase in text for phrase in ("not found", "does not exist", "not loaded"))


def _reject_user_unit(home, env):
    path = unit_file(home, env)
    if path.is_file():
        raise ServiceInstallError(
            "A user service is already installed. Remove it with: alphagsm agent uninstall-service"
        )


def _reject_system_unit(directory):
    path = system_unit_file(directory)
    if path.is_file():
        raise ServiceInstallError(
            "A system service is already installed. Remove it with: alphagsm agent uninstall-service --system"
        )


def _require_system_write(path):
    parent = path.parent
    if parent.exists() and not os.access(parent, os.W_OK):
        raise ServiceInstallError(
            "System install needs root to write " + str(path) + ". "
            "Use alphagsm agent install-service without --system for a user service."
        )


def _write_unit(path, text):
    if path.is_symlink() or path.parent.is_symlink():
        raise ServiceInstallError("Refusing to write the agent service through a symlink")
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    except OSError as exc:
        raise ServiceInstallError("Could not create the systemd directory: " + str(exc)) from exc
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
