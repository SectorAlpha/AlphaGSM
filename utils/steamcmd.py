from utils.settings import settings 
import pwd
import os
import os.path
import subprocess as sp

from downloadermodules.url import download as url_download

# if a user has already installed steam to e.g ubuntu, steamcmd prefers to be installed in the same directory (or at least when steamcmd starts, it sends the error related things there as if it wants to be installed there.
STEAMCMD_DIR = os.path.expanduser(settings.user.downloader.getsection('steamcmd').get('steamcmd_path') or "~/.local/share/Steam/" if os.path.isdir(os.path.expanduser("~/.local/share/Steam/")) else "~/Steam/")
STEAMCMD_EXE = STEAMCMD_DIR + "steamcmd.sh"
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
STEAMCMD_SCRIPTS = os.path.expanduser(settings.user.getsection('steamcmd').get('steamcmd_scripts',os.path.join(settings.user.getsection('core').get("alphagsm_path","~/.alphagsm"),"steamcmd_scripts" )))
STEAMCMD_GAMEUPDATE_TEMPLATE = "steamcmd_gamescript_template.txt"
# check if steamcmd exists, if not download it and install it via wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
# execute steamcmd/steamcmd.sh
# <user> = Anonymous by default
# ./steamcmd +login <user> +force_install_dir <download_location> +app_update <appid> +quit

def install_steamcmd():

    # if steamcmd dir does not exist, download it
    if not os.path.exists(STEAMCMD_DIR):
        os.makedirs(STEAMCMD_DIR)

    if not os.path.isfile(STEAMCMD_EXE):
        # if steamcmd files do not exist, download it
        url_download(STEAMCMD_DIR,(STEAMCMD_URL,"steamcmd_linux.tar.gz","tar.gz"))


def download(path,Steam_AppID,steam_anonymous_login_possible,validate=True):
    """ downloads a game via steamcmd"""
    # check to see if steamcmd exists
    install_steamcmd()

    # run steamcmd
    if steam_anonymous_login_possible == True:
        print("Running SteamCMD")
        proc_list = [STEAMCMD_EXE,"+login","anonymous","+force_install_dir",path,"+app_update",str(Steam_AppID),"+quit"]
        if validate == True:
            proc_list.insert(-1,"validate")
        sp.call(proc_list)
    else:
        print("no support for normal SteamCMD logins yet.")


def get_autoupdate_script(name,path,app_id,force=False):
    """
    Gets the autoupdate script
    If it does not exist, write it
    Write it anyway if force = True
    """
    if not os.path.isdir(STEAMCMD_SCRIPTS):
        os.mkdir(STEAMCMD_SCRIPTS)
    file_name = os.path.join(STEAMCMD_SCRIPTS, '') + name + "_update.txt"
    if not os.path.isfile(file_name) or (force == True):
        steamcmd_gameupdate_text = open(os.path.join(os.path.abspath(os.path.dirname(__file__)),STEAMCMD_GAMEUPDATE_TEMPLATE), 'r').read()
        steamcmd_gameupdate_text = steamcmd_gameupdate_text % (path,app_id)
        f = open(file_name,"w")
        f.write(steamcmd_gameupdate_text)
        f.close()
    return file_name
