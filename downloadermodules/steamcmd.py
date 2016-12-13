# WARNING, THIS MODULE IS NOT SUPPORTED FOR NOW
# USE AT YOUR OWN RISK
# Or message the developers if you would like to help get this working.
# There may be major bugs and errors and it isn't at all tested.
from utils.settings import settings 
from . import url as urlextra
import downloader.downloader as downloader
import pwd
import os
import os.path
import shutil



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
  if not os.path.exists(steam_cmd_install_dir):
    os.makedirs(STEAMCMD_DIR)

  if not os.path.isfile(STEAMCMD_EXE):
    # if steamcmd files do not exist, download it
    urlextra.download(STEAMCMD_DIR,(STEAMCMD_IRL,"steamcmd_linux.tar.gz","tar.gz"))


def download(path,args):
  """ downloads a game via steamcmd"""
  Steam_AppID, version, steam_anonymous_login_possible = *args
  version = int(version)
  # check to see if steamcmd exists
  install_steamcmd()
  # run steamcmd
  existing = downloader.getpaths("steamcmd", sort = "version", Steam_AppID = Steam_AppID, steam_anonymous_login_possible = steam_anonymous_login_possible)

  if len(existing) > 0:
    lmodule,largs,llocation,ldate,lactive = existing[0]
    shutil.copytree(llocation,path)
 
  if bool(steam_anonymous_login_possible):
    print("Running SteamCMD")
    proc_list = [STEAMCMD_EXE,"+login","anonymous","+force_install_dir",path,"+app_update",str(Steam_AppID),"+quit"]
    sp.call(proc_list)
  else:
    print("no support for normal SteamCMD logins yet.")

def getfilter(active=None,Steam_AppID=None,steam_anonymous_login_possible=None,sort=None):
  filterfn=_true
  sortfn=None
  if active!=None:
    active=bool(active)
    if Steam_AppID!=None:
      if steam_anonymous_login_possible!=None:
        filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive and str(Steam_AppID) == largs[0] and str(steam_anonymous_login_possible) == largs[2]
      else
        filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive and str(Steam_AppID) == largs[0]
    elif steam_anonymous_login_possible!=None:
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive and str(steam_anonymous_login_possible) == largs[2]
    else
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive
  elif Steam_AppID!=None:    
    if steam_anonymous_login_possible!=None:
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: str(Steam_AppID) == largs[0] and str(steam_anonymous_login_possible) == largs[2]
    else
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: str(Steam_AppID) == largs[0]
  else if steam_anonymous_login_possible!=None:
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: str(steam_anonymous_login_possible) == largs[2]
  if sort == "version":
    sortfn=lambda lmodule,largs,llocation,ldate,lactive: int(largs[1])
  elif sort != None:
    raise DownloaderError("Unknown sort key")
  return filterfn,sortfn

def _true(*arg):
  return True
