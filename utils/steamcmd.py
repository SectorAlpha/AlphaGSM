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
# check if steamcmd exists, if not download it and install it via wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
# execute steamcmd/steamcmd.sh
# <user> = Anonymous by default
# ./steamcmd +login <user> +force_install_dir <download_location> +app_update <appid> +quit


def _normalise_install_path(path):
    return os.path.abspath(os.path.expanduser(path))


def _steamcmd_succeeded(output, app_id):
    success_markers = (
        "Success! App '{}' fully installed.".format(app_id),
        "Success! App '{}' already up to date.".format(app_id),
    )
    return any(marker in output for marker in success_markers)


def install_steamcmd():

    # if steamcmd dir does not exist, download it
    if not os.path.exists(STEAMCMD_DIR):
        os.makedirs(STEAMCMD_DIR)

    if not os.path.isfile(STEAMCMD_EXE):
        # if steamcmd files do not exist, download it
        url_download(STEAMCMD_DIR, (STEAMCMD_URL, "steamcmd_linux.tar.gz", "tar.gz"))


def download(path, Steam_AppID, steam_anonymous_login_possible, validate=True):
    """downloads a game via steamcmd"""
    # check to see if steamcmd exists
    install_steamcmd()
    path = _normalise_install_path(path)

    # run steamcmd
    if steam_anonymous_login_possible:
        print("Running SteamCMD")
        proc_list = [
            STEAMCMD_EXE,
            "+force_install_dir",
            path,
            "+login",
            "anonymous",
            "+app_update",
            str(Steam_AppID),
            "+quit",
        ]
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
                return
            if attempt + 1 < STEAMCMD_RETRIES:
                print("SteamCMD did not complete install cleanly, retrying...")
                time.sleep(2)
        raise sp.CalledProcessError(proc.returncode, proc_list, output=last_output)
    else:
        print("no support for normal SteamCMD logins yet.")


def get_autoupdate_script(name, path, app_id, force=False):
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
        steamcmd_gameupdate_text = steamcmd_gameupdate_text % (path, app_id)
        f = open(file_name, "w")
        f.write(steamcmd_gameupdate_text)
        f.close()
    return file_name
