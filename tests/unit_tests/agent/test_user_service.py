"""The optional agent service installs only the foreground run command."""

import os
import ssl
import subprocess
import sys
from pathlib import Path

import pytest

from agent.cli import run
from agent.config import Config
from agent.tls import client_context
from agent.user_service import (
    Account,
    ServiceInstallError,
    UNIT_NAME,
    install,
    install_hint,
    lookup_account,
    render_unit,
    resolve_executable,
    systemd_quote,
    uninstall,
)
from core.main import main as dispatch_main


def _program(path):
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _ok(argv, code=0, out="", err=""):
    return subprocess.CompletedProcess(argv, code, out, err)


def _runner(calls, *, fail_at=None, linger=""):
    def run_command(argv):
        calls.append(list(argv))
        if fail_at is not None and list(argv) == fail_at:
            return _ok(argv, 1, "", "permission denied")
        if argv[:1] == ["loginctl"]:
            return _ok(argv, 0, linger, "")
        return _ok(argv)

    return run_command


def _which(_name):
    return "/usr/bin/systemctl"


def test_client_context_refuses_tls_1_0_and_1_1():
    context = client_context()
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_unit_quotes_the_program_and_keeps_consent_out(tmp_path):
    program = "/srv/AlphaGSM 1/alphagsm%bin"
    text = render_unit(program, str(tmp_path / "my config.conf"))
    assert "ExecStart=" + systemd_quote(program) + " agent run" in text
    assert 'Environment=ALPHAGSM_CONFIG_LOCATION="' + str(tmp_path / "my config.conf") + '"' in text
    assert "enable-reporting" not in text
    assert "enable-management" not in text
    assert "credential" not in text
    assert render_unit(program).count("Environment=") == 0


def test_install_writes_a_user_unit_and_restarts_it(tmp_path, capsys):
    program = _program(tmp_path / "alphagsm")
    calls = []
    install(
        str(program),
        runner=_runner(calls, linger="Linger=no\n"),
        home=tmp_path / "home",
        env={"ALPHAGSM_CONFIG_LOCATION": str(tmp_path / "alphagsm.conf")},
        platform="linux",
        user="tester",
        which=_which,
    )
    unit = tmp_path / "home" / ".config" / "systemd" / "user" / UNIT_NAME
    assert unit.read_text(encoding="utf-8").startswith("[Unit]\n")
    assert oct(unit.stat().st_mode & 0o777) == "0o644"
    assert calls[:3] == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", UNIT_NAME],
        ["systemctl", "--user", "restart", UNIT_NAME],
    ]
    assert calls[3] == ["loginctl", "show-user", "tester", "-p", "Linger"]
    assert not any("enable-linger" in part for call in calls for part in call)
    output = capsys.readouterr().out
    assert "Installed the user service " + UNIT_NAME + " and started it." in output
    assert "alphagsm-agent run" not in unit.read_text(encoding="utf-8")
    assert "Reporting and management are unchanged." in output
    assert "loginctl enable-linger" in output
    assert not (tmp_path / "agent" / "config.json").exists()


def test_install_failure_leaves_consent_untouched(tmp_path):
    program = _program(tmp_path / "alphagsm")
    agent = tmp_path / "agent"
    Config(agent)
    before = list(agent.iterdir())
    calls = []
    with pytest.raises(ServiceInstallError, match="enable"):
        install(
            str(program),
            runner=_runner(calls, fail_at=["systemctl", "--user", "enable", UNIT_NAME]),
            home=tmp_path / "home",
            env={},
            platform="linux",
            user="",
            which=_which,
        )
    assert list(agent.iterdir()) == before
    assert (tmp_path / "home" / ".config" / "systemd" / "user" / UNIT_NAME).is_file()


def test_install_refuses_other_platforms_and_missing_systemctl(tmp_path):
    calls = []
    with pytest.raises(ServiceInstallError, match="Linux systemd"):
        install("/bin/alphagsm", runner=_runner(calls), platform="windows", which=_which)
    assert calls == []
    with pytest.raises(ServiceInstallError, match="systemctl is not available"):
        install(str(_program(tmp_path / "alphagsm")), runner=_runner(calls), platform="linux", which=lambda _name: None)
    assert calls == []
    assert not (tmp_path / "home").exists()


def test_install_refuses_a_symlinked_unit(tmp_path):
    program = _program(tmp_path / "alphagsm")
    unit_dir = tmp_path / "config" / "systemd" / "user"
    unit_dir.mkdir(parents=True)
    target = tmp_path / "other.service"
    target.write_text("keep\n", encoding="utf-8")
    (unit_dir / UNIT_NAME).symlink_to(target)
    with pytest.raises(ServiceInstallError, match="symlink"):
        install(
            str(program),
            runner=_runner([]),
            env={"XDG_CONFIG_HOME": str(tmp_path / "config")},
            platform="linux",
            which=_which,
        )
    assert target.read_text(encoding="utf-8") == "keep\n"


def test_uninstall_removes_only_the_unit(tmp_path, capsys):
    program = _program(tmp_path / "alphagsm")
    env = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    install(str(program), runner=_runner([]), env=env, platform="linux", user="", which=_which)
    calls = []
    uninstall(runner=_runner(calls), env=env, platform="linux", which=_which)
    assert calls == [
        ["systemctl", "--user", "disable", "--now", UNIT_NAME],
        ["systemctl", "--user", "daemon-reload"],
    ]
    assert not (tmp_path / "config" / "systemd" / "user" / UNIT_NAME).exists()
    assert "permissions are unchanged" in capsys.readouterr().out
    uninstall(runner=_runner(calls), env=env, platform="linux", which=_which)
    assert "No AlphaGSM user service is installed." in capsys.readouterr().out


def test_ordinary_import_does_not_load_linux_account_modules():
    env = os.environ.copy()
    root = Path(__file__).resolve().parents[3]
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), env.get("PYTHONPATH", "")])
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys\n"
            "import agent.user_service\n"
            "raise SystemExit('grp' in sys.modules or 'pwd' in sys.modules)\n",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr


def test_unsafe_program_paths_are_rejected(tmp_path):
    with pytest.raises(ServiceInstallError, match="unsupported characters"):
        resolve_executable(str(tmp_path / "alpha\ngsm"))
    plain = tmp_path / "alphagsm"
    plain.write_text("nope\n", encoding="utf-8")
    with pytest.raises(ServiceInstallError, match="executable"):
        resolve_executable(str(plain))


def test_cli_install_does_not_create_agent_state(tmp_path, monkeypatch):
    seen = {}

    def fake(executable, **_kwargs):
        seen["executable"] = executable

    monkeypatch.setattr("agent.user_service.install", fake)
    assert run(["install-service"], root=tmp_path / "agent", executable=str(tmp_path / "alphagsm")) == 0
    assert seen["executable"] == str(tmp_path / "alphagsm")
    assert not (tmp_path / "agent").exists()


def test_cli_rejects_a_non_linux_service_install(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("agent.user_service.PLATFORM", "macos")
    assert run(["install-service"], root=tmp_path / "agent") == 1
    assert "Linux systemd" in capsys.readouterr().out
    assert not (tmp_path / "agent").exists()


def test_main_dispatches_the_invoked_program(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "agent.user_service.install", lambda executable, **_kwargs: seen.update(executable=executable)
    )
    assert dispatch_main("/opt/AlphaGSM/alphagsm", ["agent", "install-service"]) == 0
    assert seen["executable"] == "/opt/AlphaGSM/alphagsm"


def test_hint_points_at_the_command_without_installing(tmp_path, monkeypatch):
    absent = tmp_path / "no-system"
    assert "foreground" in install_hint(platform="windows")
    assert "install-service --system" in install_hint(
        platform="linux", which=_which, home=tmp_path, env={}, system_dir=absent
    )
    unit = tmp_path / ".config" / "systemd" / "user"
    unit.mkdir(parents=True)
    (unit / UNIT_NAME).write_text("[Unit]\n", encoding="utf-8")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert install_hint(
        platform="linux", which=_which, home=tmp_path, env={}, system_dir=absent
    ).startswith("Restart the installed")


def test_percent_and_quotes_are_escaped():
    assert systemd_quote('/opt/a"b\\c%') == '"/opt/a\\"b\\\\c%%"'


def test_system_service_runs_alphagsm_agent_run_as_the_operator(tmp_path, capsys):
    program = _program(tmp_path / "alphagsm")
    account = Account("games", "games", str(tmp_path / "home" / "games"))
    calls = []
    install(
        str(program),
        runner=_runner(calls),
        home=tmp_path / "home",
        env={"ALPHAGSM_CONFIG_LOCATION": str(tmp_path / "alphagsm.conf")},
        platform="linux",
        which=_which,
        system=True,
        account=account,
        system_dir=tmp_path / "systemd",
    )
    text = (tmp_path / "systemd" / UNIT_NAME).read_text(encoding="utf-8")
    assert "ExecStart=" + systemd_quote(str(program)) + " agent run" in text
    assert "alphagsm-agent" not in text
    assert "User=games" in text
    assert "Group=games" in text
    assert "Environment=HOME=" + systemd_quote(account.home) in text
    assert "WantedBy=multi-user.target" in text
    assert "WantedBy=default.target" not in text
    assert calls == [
        ["systemctl", "daemon-reload"],
        ["systemctl", "enable", UNIT_NAME],
        ["systemctl", "restart", UNIT_NAME],
    ]
    output = capsys.readouterr().out
    assert "system service" in output
    assert "runs as games" in output
    calls.clear()
    uninstall(
        runner=_runner(calls),
        platform="linux",
        which=_which,
        system=True,
        system_dir=tmp_path / "systemd",
    )
    assert calls[0] == ["systemctl", "disable", "--now", UNIT_NAME]
    assert not (tmp_path / "systemd" / UNIT_NAME).exists()


def test_system_and_user_services_are_not_installed_together(tmp_path):
    program = _program(tmp_path / "alphagsm")
    home = tmp_path / "home"
    system_dir = tmp_path / "systemd"
    install(
        str(program),
        runner=_runner([]),
        home=home,
        env={},
        platform="linux",
        user="",
        which=_which,
        system_dir=system_dir,
    )
    with pytest.raises(ServiceInstallError, match="user service is already installed"):
        install(
            str(program),
            runner=_runner([]),
            home=home,
            env={},
            platform="linux",
            which=_which,
            system=True,
            account=Account("games", "games", str(home / "games")),
            system_dir=system_dir,
        )
    assert not (system_dir / UNIT_NAME).exists()


def test_system_install_needs_a_writable_directory_and_refuses_root(tmp_path):
    program = _program(tmp_path / "alphagsm")
    system_dir = tmp_path / "systemd"
    system_dir.mkdir()
    system_dir.chmod(0o555)
    try:
        with pytest.raises(ServiceInstallError, match="needs root"):
            install(
                str(program),
                runner=_runner([]),
                platform="linux",
                which=_which,
                system=True,
                account=Account("games", "games", "/home/games"),
                system_dir=system_dir,
            )
    finally:
        system_dir.chmod(0o755)
    with pytest.raises(ServiceInstallError, match="does not run as root"):
        lookup_account("root")
    with pytest.raises(ServiceInstallError, match="Unknown service account"):
        lookup_account("no-such-alphagsm-user")


def test_cli_system_install_uses_the_service_account(tmp_path, monkeypatch):
    seen = {}

    def fake(executable, system=False, user=None, **_kwargs):
        seen.update(executable=executable, system=system, user=user)

    monkeypatch.setattr("agent.user_service.install", fake)
    assert run(
        ["install-service", "--system", "--service-user", "games"],
        root=tmp_path / "agent",
        executable="/opt/alphagsm",
    ) == 0
    assert seen == {"executable": "/opt/alphagsm", "system": True, "user": "games"}
    assert run(["install-service", "--service-user", "games"], root=tmp_path / "agent") == 1
    assert not (tmp_path / "agent").exists()
