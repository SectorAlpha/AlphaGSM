import os

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
    monkeypatch.setattr(steamcmd_module.sp, "call", lambda cmd: calls.append(cmd) or 0)
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


def test_download_skips_subprocess_for_non_anonymous_login(monkeypatch, capsys):
    monkeypatch.setattr(steamcmd_module, "install_steamcmd", lambda: None)
    monkeypatch.setattr(steamcmd_module.sp, "call", lambda cmd: (_ for _ in ()).throw(AssertionError("should not run")))

    steamcmd_module.download("/srv/game", 232250, False)

    assert "no support for normal SteamCMD logins yet." in capsys.readouterr().out


def test_get_autoupdate_script_writes_template(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "scripts"
    template = tmp_path / "steamcmd_gamescript_template.txt"
    template.write_text("force_install_dir %s\nlogin anonymous\napp_update %s\n")
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
