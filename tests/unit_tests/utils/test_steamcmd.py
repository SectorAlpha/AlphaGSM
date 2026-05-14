import os
import subprocess as sp

import utils.steamcmd as steamcmd_module


def test_install_steamcmd_creates_directory_and_downloads_when_missing(tmp_path, monkeypatch):
    downloads = []
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_DIR", str(tmp_path / "steam") + "/")
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", str(tmp_path / "steam" / "steamcmd.sh"))
    monkeypatch.setattr(steamcmd_module, "url_download", lambda path, args: downloads.append((path, args)))

    steamcmd_module.install_steamcmd()

    assert os.path.isdir(steamcmd_module.STEAMCMD_DIR)
    assert downloads == [
        (
            steamcmd_module.STEAMCMD_DIR,
            (steamcmd_module.STEAMCMD_URL, "steamcmd_linux.tar.gz", "tar.gz"),
        )
    ]


def test_download_runs_steamcmd_with_validate(monkeypatch):
    calls = []
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: calls.append("install"))
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: (
            calls.append(cmd)
            or sp.CompletedProcess(cmd, 0, "Success! App '232250' fully installed.\n")
        ),
    )
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: "/abs/" + path)

    steamcmd_module.download("srv/game", 232250, True, validate=True)

    assert calls[0] == "install"
    assert calls[1] == [
        "/steam/steamcmd.sh",
        "+force_install_dir",
        "/abs/srv/game",
        "+login",
        "anonymous",
        "+app_update",
        "232250",
        "validate",
        "+quit",
    ]


def test_download_includes_goldsrc_mod_configuration(monkeypatch):
    calls = []
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: calls.append("install"))
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: (
            calls.append(cmd)
            or sp.CompletedProcess(cmd, 0, "Success! App '90' fully installed.\n")
        ),
    )
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: "/abs/" + path)

    steamcmd_module.download("srv/game", 90, True, validate=False, mod="cstrike")

    assert calls[1] == [
        "/steam/steamcmd.sh",
        "+force_install_dir",
        "/abs/srv/game",
        "+login",
        "anonymous",
        "+app_set_config",
        "90",
        "mod",
        "cstrike",
        "+app_update",
        "90",
        "+quit",
    ]


def test_download_retries_until_steamcmd_reports_success(monkeypatch):
    outputs = [
        sp.CompletedProcess(["cmd"], 0, "Steam Console Client bootstrap\n"),
        sp.CompletedProcess(["cmd"], 0, "Success! App '232250' already up to date.\n"),
    ]
    calls = []

    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: path)
    monkeypatch.setattr(steamcmd_module.time, "sleep", lambda seconds: calls.append(("sleep", seconds)))
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: calls.append(cmd) or outputs.pop(0),
    )

    steamcmd_module.download("/srv/game", 232250, True, validate=False)

    assert calls[0][0] == "/steam/steamcmd.sh"
    assert calls[1] == ("sleep", 2)
    assert calls[2][0] == "/steam/steamcmd.sh"


def test_download_raises_when_steamcmd_never_reports_success(monkeypatch):
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: path)
    monkeypatch.setattr(steamcmd_module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: sp.CompletedProcess(
            cmd,
            0,
            "ERROR! Failed to install app '232250' (Missing configuration)\n",
        ),
    )

    try:
        steamcmd_module.download("/srv/game", 232250, True, validate=False)
    except sp.CalledProcessError as ex:
        assert ex.returncode == 0
        assert "Missing configuration" in ex.output
    else:
        raise AssertionError("Expected steamcmd download failure to raise CalledProcessError")


def test_steamcmd_state_202_flake_matches_known_bare_flake_app_ids():
    assert steamcmd_module._steamcmd_state_202_flake(
        "Error! App '232130' state is 0x202 after update job.",
        232130,
    )
    assert steamcmd_module._steamcmd_state_202_flake(
        "Error! App '346680' state is 0x202 after update job.",
        346680,
    )
    assert steamcmd_module._steamcmd_state_202_flake(
        "Error! App '746200' state is 0x202 after update job.",
        746200,
    )


def test_steamcmd_retry_delay_uses_reconfig_delay_for_known_bare_state_202_flakes():
    assert (
        steamcmd_module._steamcmd_retry_delay(
            "Error! App '418480' state is 0x202 after update job.",
            418480,
        )
        == steamcmd_module.STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS
    )
    assert (
        steamcmd_module._steamcmd_retry_delay(
            "Error! App '746200' state is 0x202 after update job.",
            746200,
        )
        == steamcmd_module.STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS
    )


def test_steamcmd_state_202_flake_does_not_match_unknown_bare_state_202_app_ids():
    assert not steamcmd_module._steamcmd_state_202_flake(
        "Error! App '317670' state is 0x202 after update job.",
        317670,
    )


def test_download_skips_subprocess_for_non_anonymous_login(monkeypatch):
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module.sp, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not run")))

    import pytest
    with pytest.raises(RuntimeError, match="SteamCMD username required"):
        steamcmd_module.download("/srv/game", 232250, False)


def test_download_forces_windows_platform_when_flag_set(monkeypatch):
    calls = []
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: calls.append("install"))
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: (
            calls.append(cmd)
            or sp.CompletedProcess(cmd, 0, "Success! App '232250' fully installed.\n")
        ),
    )
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: "/abs/" + path)

    steamcmd_module.download("srv/game", 232250, True, validate=False, force_windows=True)

    cmd = calls[1]
    assert "+@sSteamCmdForcePlatformType" in cmd
    platform_idx = cmd.index("+@sSteamCmdForcePlatformType")
    assert cmd[platform_idx + 1] == "windows"
    # Platform override must come before app_update
    assert platform_idx < cmd.index("+app_update")


def test_download_does_not_add_platform_flag_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: calls.append("install"))
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: (
            calls.append(cmd)
            or sp.CompletedProcess(cmd, 0, "Success! App '232250' fully installed.\n")
        ),
    )
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: "/abs/" + path)

    steamcmd_module.download("srv/game", 232250, True, validate=False)

    cmd = calls[1]
    assert "+@sSteamCmdForcePlatformType" not in cmd


def test_download_workshop_item_runs_steamcmd_and_returns_content_dir(tmp_path, monkeypatch):
    calls = []
    content_dir = tmp_path / "workshop" / "steamapps" / "workshop" / "content" / "440" / "12345"

    def fake_run(cmd, stdout, stderr, text, check):
        calls.append(cmd)
        content_dir.mkdir(parents=True)
        return sp.CompletedProcess(cmd, 0, "Workshop item downloaded\n")

    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: calls.append("install"))
    monkeypatch.setattr(steamcmd_module.sp, "run", fake_run)
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: str(tmp_path / "workshop"))

    result = steamcmd_module.download_workshop_item("ignored", 440, 12345, True)

    assert result == str(content_dir)
    assert calls[0] == "install"
    assert calls[1] == [
        "/steam/steamcmd.sh",
        "+force_install_dir",
        str(tmp_path / "workshop"),
        "+login",
        "anonymous",
        "+workshop_download_item",
        "440",
        "12345",
        "+quit",
    ]


def test_download_workshop_item_raises_when_content_dir_never_appears(monkeypatch):
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: path)
    monkeypatch.setattr(steamcmd_module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: sp.CompletedProcess(
            cmd,
            0,
            "ERROR! Failed to download workshop item\n",
        ),
    )

    import pytest
    with pytest.raises(sp.CalledProcessError):
        steamcmd_module.download_workshop_item("/srv/workshop", 440, 12345, True)


def test_get_autoupdate_script_writes_template(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "scripts"
    template = tmp_path / "steamcmd_gamescript_template.txt"
    template.write_text("force_install_dir %s\nlogin anonymous\n%sapp_update %s\n")
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_SCRIPTS", str(scripts_dir))
    monkeypatch.setattr(steamcmd_module.os.path, "dirname", lambda path: str(tmp_path))
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path.replace("~", "/home/tester"))
    monkeypatch.setattr(
        steamcmd_module.os.path,
        "abspath",
        lambda path: "/abs" + path if path == "/home/tester/srv/game" else path,
    )

    path = steamcmd_module.get_autoupdate_script("alpha", "~/srv/game", 232250, force=True)

    assert path == str(scripts_dir / "alpha_update.txt")
    assert (scripts_dir / "alpha_update.txt").read_text() == (
        "force_install_dir /abs/home/tester/srv/game\n"
        "login anonymous\n"
        "app_update 232250\n"
    )


def test_get_autoupdate_script_writes_goldsrc_mod_line(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "scripts"
    template = tmp_path / "steamcmd_gamescript_template.txt"
    template.write_text("force_install_dir %s\nlogin anonymous\n%sapp_update %s\n")
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_SCRIPTS", str(scripts_dir))
    monkeypatch.setattr(steamcmd_module.os.path, "dirname", lambda path: str(tmp_path))
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: path)

    path = steamcmd_module.get_autoupdate_script("goldsrc", "/srv/game", 90, force=True, mod="dod")

    assert path == str(scripts_dir / "goldsrc_update.txt")
    assert (scripts_dir / "goldsrc_update.txt").read_text() == (
        "force_install_dir /srv/game\n"
        "login anonymous\n"
        "app_set_config 90 mod dod\n"
        "app_update 90\n"
    )
