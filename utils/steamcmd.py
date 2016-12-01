#todo 

from utils.settings import settings 
import pwd
import os
import subprocess as sp

from downloadermodules.url import download as url_download

USER=settings.system.downloader.get('user') or pwd.getpwuid(os.getuid()).pw_name
# if a user has already installed steam to e.g ubuntu, steamcmd prefers to be installed in the same directory (or at least when steamcmd starts, it sends the error related things there as if it wants to be installed there.
STEAMCMD_DIR = settings.system.downloader.get('steamcmd_path') or "/home/" + pwd.getpwuid(os.getuid()).pw_name + "/.local/share/Steam/" if os.path.isdir( "/home/" + pwd.getpwuid(os.getuid()).pw_name + "/.local/share/Steam/") else "/home/" + pwd.getpwuid(os.getuid()).pw_name + "/Steam/"
STEAMCMD_EXE = STEAMCMD_DIR + "steamcmd.sh"
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"

# check if steamcmd exists, if not download it and install it via wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
# execute steamcmd/steamcmd.sh
# <user> = Anonymous by default
# ./steamcmd +login <user> +force_install_dir <download_location> +app_update <appid> +quit

def install_steamcmd():

  # if steamcmd dir does not exist, download it
  print (os.path.isdir( "/home/" + pwd.getpwuid(os.getuid()).pw_name + "/.local/share/Steam/"))
  print ("/home/" + pwd.getpwuid(os.getuid()).pw_name + "/.local/share/Steam/")
  print(STEAMCMD_DIR)
  if not os.path.exists(STEAMCMD_DIR):
    os.makedirs(STEAMCMD_DIR)

  print(STEAMCMD_EXE)
  if not os.path.isfile(STEAMCMD_EXE):
    # if steamcmd files do not exist, download it
    url_download(STEAMCMD_DIR,(STEAMCMD_URL,"steamcmd_linux.tar.gz","tar"))


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

