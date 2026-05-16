"""SteamCMD installation and game-download helpers used by Steam game modules."""

import os
import os.path
import subprocess as sp
import time

from downloadermodules.url import download as url_download
from utils.settings import settings

# if a user has already installed steam to e.g ubuntu, steamcmd prefers to be installed in the same directory (or at least when steamcmd starts, it sends the error related things there as if it wants to be installed there.
STEAMCMD_DIR = os.path.expanduser(
    settings.user.downloader.getsection("steamcmd").get("steamcmd_path")
    or "~/.local/share/Steam/"
    if os.path.isdir(os.path.expanduser("~/.local/share/Steam/"))
    else "~/Steam/"
)
STEAMCMD_EXE = STEAMCMD_DIR + "steamcmd.sh"
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
STEAMCMD_SCRIPTS = os.path.expanduser(
    settings.user.getsection("steamcmd").get(
        "steamcmd_scripts",
        os.path.join(
            settings.user.getsection("core").get("alphagsm_path", "~/.alphagsm"),
            "steamcmd_scripts",
        ),
    )
)
STEAMCMD_GAMEUPDATE_TEMPLATE = "steamcmd_gamescript_template.txt"
STEAMCMD_RETRIES = 3
STEAMCMD_RETRY_DELAY_SECONDS = 2
STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS = 5
_KNOWN_BARE_STATE_202_FLAKE_APP_IDS = frozenset({"232130", "346680", "418480", "746200"})
# check if steamcmd exists, if not download it and install it via wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
# execute steamcmd/steamcmd.sh
# <user> = Anonymous by default
# ./steamcmd +login <user> +force_install_dir <download_location> +app_update <appid> +quit


def _normalise_install_path(path):
    """Return an absolute, user-expanded install path for SteamCMD commands."""
    return os.path.abspath(os.path.expanduser(path))


def _steamcmd_succeeded(output, app_id):
    """Return whether SteamCMD output includes a success marker for the app."""
    success_markers = (
        "Success! App '{}' fully installed.".format(app_id),
        "Success! App '{}' already up to date.".format(app_id),
    )
    return any(marker in output for marker in success_markers)


def _steamcmd_missing_manifest_flake(output, app_id):
    """Return whether SteamCMD reported the known missing-manifest flake."""

    if app_id in (None, ""):
        return False

    app_id = str(app_id)
    missing_config = "ERROR! Failed to install app '{}' (Missing configuration)".format(app_id)
    state_202 = "Error! App '{}' state is 0x202 after update job.".format(app_id)
    return missing_config in output and state_202 in output


def _steamcmd_state_202_flake(output, app_id):
    """Return whether SteamCMD reported a known transient state 0x202 flake."""

    if app_id in (None, ""):
        return False

    app_id = str(app_id)
    state_202 = "Error! App '{}' state is 0x202 after update job.".format(app_id)
    if state_202 not in output:
        return False

    return _steamcmd_missing_manifest_flake(output, app_id) or app_id in _KNOWN_BARE_STATE_202_FLAKE_APP_IDS


def _steamcmd_retry_delay(output, app_id):
    """Return the retry delay for known transient SteamCMD states."""

    if _steamcmd_state_202_flake(output, app_id):
        return STEAMCMD_RETRY_DELAY_RECONFIG_SECONDS
    return STEAMCMD_RETRY_DELAY_SECONDS


def _get_login_args(steam_anonymous_login_possible):
    """Return the SteamCMD login arguments for anonymous or owned-game installs."""

    if steam_anonymous_login_possible:
        return ["+login", "anonymous"]
    username = settings.user.downloader.getsection("steamcmd").get("username")
    password = settings.user.downloader.getsection("steamcmd").get("password", "")
    if not username:
        raise RuntimeError(
            "SteamCMD username required for this server. Set [downloader.steamcmd] username in alphagsm.conf"
        )
    return ["+login", str(username), str(password)]


def _ensure_steamclient_symlinks():
    """Create ~/.steam/sdk{32,64}/steamclient.so symlinks expected by many
    dedicated server binaries.

    Many Steamworks-SDK game servers look for steamclient.so in the well-known
    paths ``~/.steam/sdk64/steamclient.so`` (64-bit) and
    ``~/.steam/sdk32/steamclient.so`` (32-bit).  SteamCMD standalone creates
    these files inside its own runtime directory but does *not* automatically
    create the ~/.steam/sdk* symlinks that the full Steam client would create.
    We create them here so that game servers relying on them start correctly.
    """
    home = os.path.expanduser("~")
    for bits in ("32", "64"):
        src = os.path.join(STEAMCMD_DIR, f"linux{bits}", "steamclient.so")
        if not os.path.isfile(src):
            continue
        dst_dir = os.path.join(home, ".steam", f"sdk{bits}")
        dst = os.path.join(dst_dir, "steamclient.so")
        if os.path.lexists(dst):
            continue
        os.makedirs(dst_dir, exist_ok=True)
        try:
            os.symlink(src, dst)
        except FileExistsError:
            continue


def install_steamcmd():
    """Ensure the SteamCMD runtime exists in the configured installation path."""

    # if steamcmd dir does not exist, download it
    if not os.path.exists(STEAMCMD_DIR):
        os.makedirs(STEAMCMD_DIR)

    if not os.path.isfile(STEAMCMD_EXE):
        # if steamcmd files do not exist, download it
        url_download(STEAMCMD_DIR, (STEAMCMD_URL, "steamcmd_linux.tar.gz", "tar.gz"))


def download(
    path,
    Steam_AppID,
    steam_anonymous_login_possible,
    validate=True,
    mod=None,
    force_windows=False,
):
    """Download a game server via SteamCMD, optionally setting a GoldSrc mod.

    Args:
        path: Installation directory for the server files.
        Steam_AppID: The Steam application ID to download.
        steam_anonymous_login_possible: Whether the app allows anonymous login.
        validate: If ``True`` pass ``validate`` to SteamCMD.
        mod: Optional GoldSrc mod name (used for app 90).
        force_windows: If ``True`` instruct SteamCMD to download the Windows
            depot rather than the native Linux one.  Required for Windows-only
            game servers that are launched via Wine or Proton on Linux.
    """
    # check to see if steamcmd exists
    install_steamcmd()
    path = _normalise_install_path(path)

    print("Running SteamCMD")
    proc_list = [STEAMCMD_EXE]
    if force_windows:
        proc_list.extend(["+@sSteamCmdForcePlatformType", "windows"])
    proc_list.extend(["+force_install_dir", path])
    proc_list.extend(_get_login_args(steam_anonymous_login_possible))
    if mod is not None:
        proc_list.extend(["+app_set_config", "90", "mod", str(mod)])
    proc_list.extend(["+app_update", str(Steam_AppID), "+quit"])
    if validate:
        proc_list.insert(-1, "validate")
    last_output = ""
    for attempt in range(STEAMCMD_RETRIES):
        proc = sp.run(
            proc_list, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, check=False
        )
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        last_output = proc.stdout
        if proc.returncode == 0 and _steamcmd_succeeded(proc.stdout, Steam_AppID):
            _ensure_steamclient_symlinks()
            return
        if attempt + 1 < STEAMCMD_RETRIES:
            retry_delay = _steamcmd_retry_delay(proc.stdout, Steam_AppID)
            print(
                "SteamCMD did not complete install cleanly, retrying in %ss..."
                % (retry_delay,)
            )
            time.sleep(retry_delay)
    raise sp.CalledProcessError(proc.returncode, proc_list, output=last_output)


def download_workshop_item(path, workshop_app_id, workshop_item_id, steam_anonymous_login_possible):
    """Download a Steam workshop item and return its extracted content directory."""

    install_steamcmd()
    path = _normalise_install_path(path)
    content_dir = os.path.join(
        path,
        "steamapps",
        "workshop",
        "content",
        str(workshop_app_id),
        str(workshop_item_id),
    )

    print("Running SteamCMD workshop download")
    proc_list = [STEAMCMD_EXE]
    proc_list.extend(["+force_install_dir", path])
    proc_list.extend(_get_login_args(steam_anonymous_login_possible))
    proc_list.extend(
        ["+workshop_download_item", str(workshop_app_id), str(workshop_item_id), "+quit"]
    )
    last_output = ""
    for attempt in range(STEAMCMD_RETRIES):
        proc = sp.run(
            proc_list, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, check=False
        )
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        last_output = proc.stdout
        if proc.returncode == 0 and os.path.isdir(content_dir):
            _ensure_steamclient_symlinks()
            return content_dir
        if attempt + 1 < STEAMCMD_RETRIES:
            retry_delay = _steamcmd_retry_delay(proc.stdout, workshop_app_id)
            print(
                "SteamCMD did not complete workshop download cleanly, retrying in %ss..."
                % (retry_delay,)
            )
            time.sleep(retry_delay)
    raise sp.CalledProcessError(proc.returncode, proc_list, output=last_output)


def get_autoupdate_script(name, path, app_id, force=False, mod=None):
    """
    Gets the autoupdate script
    If it does not exist, write it
    Write it anyway if force = True
    """
    if not os.path.isdir(STEAMCMD_SCRIPTS):
        os.mkdir(STEAMCMD_SCRIPTS)
    file_name = os.path.join(STEAMCMD_SCRIPTS, "") + name + "_update.txt"
    if not os.path.isfile(file_name) or force:
        path = _normalise_install_path(path)
        steamcmd_gameupdate_text = open(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)), STEAMCMD_GAMEUPDATE_TEMPLATE
            ),
            "r",
        ).read()
        mod_line = ""
        if mod is not None:
            mod_line = "app_set_config 90 mod %s\n" % (mod,)
        steamcmd_gameupdate_text = steamcmd_gameupdate_text % (path, mod_line, app_id)
        f = open(file_name, "w")
        f.write(steamcmd_gameupdate_text)
        f.close()
    return file_name
