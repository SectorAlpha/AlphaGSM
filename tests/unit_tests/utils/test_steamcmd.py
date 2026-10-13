import os
import subprocess as sp
import pytest

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
        "Error! App '294420' state is 0x202 after update job.",
        294420,
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
            "Error! App '294420' state is 0x202 after update job.",
            294420,
        )
        == steamcmd_module.STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS
    )
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


def test_download_retries_bare_state_202_for_sevendaystodie(monkeypatch):
    outputs = [
        sp.CompletedProcess(
            ["cmd"],
            0,
            "Error! App '294420' state is 0x202 after update job.\n",
        ),
        sp.CompletedProcess(
            ["cmd"],
            0,
            "Success! App '294420' fully installed.\n",
        ),
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

    steamcmd_module.download("/srv/game", 294420, True, validate=False)

    assert calls[1] == ("sleep", steamcmd_module.STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS)


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


def test_download_forces_named_platform_when_requested(monkeypatch):
    calls = []
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: calls.append("install"))
    monkeypatch.setattr(
        steamcmd_module.sp,
        "run",
        lambda cmd, stdout, stderr, text, check: (
            calls.append(cmd)
            or sp.CompletedProcess(cmd, 0, "Success! App '222860' fully installed.\n")
        ),
    )
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")
    monkeypatch.setattr(steamcmd_module.os.path, "expanduser", lambda path: path)
    monkeypatch.setattr(steamcmd_module.os.path, "abspath", lambda path: "/abs/" + path)

    steamcmd_module.download(
        "srv/game",
        222860,
        True,
        validate=False,
        force_platform="linux",
    )

    cmd = calls[1]
    assert "+@sSteamCmdForcePlatformType" in cmd
    platform_idx = cmd.index("+@sSteamCmdForcePlatformType")
    assert cmd[platform_idx + 1] == "linux"
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


@pytest.mark.parametrize("identifier", [12345, "https://steamcommunity.com/sharedfiles/filedetails/?id=12345"])
def test_download_workshop_item_runs_steamcmd_and_returns_content_dir(tmp_path, monkeypatch, identifier):
    calls = []
    content_dir = tmp_path / "workshop" / "steamapps" / "workshop" / "content" / "440" / "12345"

    def fake_run(cmd, stdout, stderr, text, check):
        calls.append(cmd)
        content_dir.mkdir(parents=True)
        (content_dir / "addon.vpk").write_bytes(b"addon")
        return sp.CompletedProcess(cmd, 0, f'Success. Downloaded item 12345 to "{content_dir}" (5 bytes)\n')

    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: calls.append("install"))
    monkeypatch.setattr(steamcmd_module.sp, "run", fake_run)
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_EXE", "/steam/steamcmd.sh")

    result = steamcmd_module.download_workshop_item(str(tmp_path / "workshop"), 440, identifier, True)

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


@pytest.mark.parametrize("output", ["ERROR! Download item failed\n",
                                   "Success. Downloaded item 999 to somewhere\n", ""])
def test_workshop_stale_content_does_not_mask_failed_download(tmp_path, monkeypatch, output):
    content = tmp_path / "steamapps/workshop/content/440/12345"
    content.mkdir(parents=True)
    (content / "old.vpk").write_bytes(b"stale")
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(steamcmd_module.sp, "run", lambda *a, **kw: sp.CompletedProcess(a[0], 0, output))
    with pytest.raises(sp.CalledProcessError):
        steamcmd_module.download_workshop_item(tmp_path, 440, 12345, True)


def test_workshop_uses_actual_steamcmd_content_root(tmp_path, monkeypatch):
    steam_root = tmp_path / "steam"
    content = steam_root / "steamapps/workshop/content/550/10"
    content.mkdir(parents=True)
    (content / "addon.vpk").write_bytes(b"addon")
    monkeypatch.setattr(steamcmd_module, "STEAMCMD_DIR", str(steam_root))
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(steamcmd_module.sp, "run", lambda *a, **kw: sp.CompletedProcess(
        a[0], 0, f'Success. Downloaded item 10 to "{content}" (5 bytes)\n'))
    assert steamcmd_module.download_workshop_item(tmp_path / "cache", 550, 10, True) == str(content)


def test_workshop_access_denied_fails_without_retry(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module.time, "sleep", lambda _: None)

    def denied(*args, **kwargs):
        calls.append(args[0])
        return sp.CompletedProcess(args[0], 0, "ERROR! Download item 10 failed (Access Denied).\n")

    monkeypatch.setattr(steamcmd_module.sp, "run", denied)
    with pytest.raises(sp.CalledProcessError) as error:
        steamcmd_module.download_workshop_item(tmp_path, 550, 10, True)
    assert "anonymous" in error.value.output.lower()
    assert len(calls) == 1


@pytest.mark.parametrize("app_id,item_id", [(0, 10), (550, "10 +quit"), (2**32, 10), (550, 0)])
def test_workshop_invalid_ids_fail_before_install(tmp_path, monkeypatch, app_id, item_id):
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: pytest.fail("must validate first"))
    with pytest.raises(ValueError):
        steamcmd_module.download_workshop_item(tmp_path, app_id, item_id, True)


def test_workshop_empty_directory_is_not_a_download(tmp_path, monkeypatch):
    content = tmp_path / "steamapps/workshop/content/550/10"
    content.mkdir(parents=True)
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(steamcmd_module.sp, "run", lambda *a, **kw: sp.CompletedProcess(
        a[0], 0, f'Success. Downloaded item 10 to "{content}" (0 bytes)\n'))
    with pytest.raises(sp.CalledProcessError):
        steamcmd_module.download_workshop_item(tmp_path, 550, 10, True)


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


def test_linux_steamcmd_installer_rejects_windows_before_files_or_download(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(steamcmd_module, 'PLATFORM', 'windows', raising=False)
    monkeypatch.setattr(steamcmd_module, 'STEAMCMD_DIR', str(tmp_path / 'steam'))
    monkeypatch.setattr(steamcmd_module, 'url_download', lambda *a: pytest.fail('must reject before download'))
    with pytest.raises(RuntimeError, match='Linux.*manager container'):
        steamcmd_module.install_steamcmd()
    assert not (tmp_path / 'steam').exists()
