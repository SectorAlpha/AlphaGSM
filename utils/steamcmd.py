from utils.settings import settings 
import pwd
import os
import os.path
import subprocess as sp
from server.server import DATAPATH

from downloadermodules.url import download as url_download

# if a user has already installed steam to e.g ubuntu, steamcmd prefers to be installed in the same directory (or at least when steamcmd starts, it sends the error related things there as if it wants to be installed there.
STEAMCMD_DIR = os.path.expanduser(settings.user.downloader.getsection('steamcmd').get('steamcmd_path') or "~/.local/share/Steam/" if os.path.isdir(os.path.expanduser("~/.local/share/Steam/")) else "~/Steam/")
STEAMCMD_EXE = STEAMCMD_DIR + "steamcmd.sh"
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"

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


def write_autoupdate_script(name,path,app_id):
  file_path = os.path.join(DATAPATH,"steamcmd_scripts/")
  print(file_path)
  if not os.path.isdir(file_path):
    os.mkdir(file_path)
  file_name = file_path + name + ".txt"
  if not os.path.isfile(file_name):
    string = make_autoupdate_string(path,app_id)
    f = open(file_name,"w")
    f.write(string)
    f.close()
  return file_name



def make_autoupdate_string(path,app_id):
  string = "@ShutdownOnFailedCommand 1\n" + \
            "@NoPromptForPassword 1\n" + \
	    "@sSteamCmdForcePlatformType linux\n" + \
	    "login anonymous\n" + \
            "force_install_dir %s\n" % path + \
            "app_update %s\n" % app_id + \
            "exit"
  return string


