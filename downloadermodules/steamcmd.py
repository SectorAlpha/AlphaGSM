#todo 

from utils.settings import settings 
from . import url as urlextra
import pwd
import os

from downloadermodules.url import download as url_download

USER=settings.system.downloader.get('user') or pwd.getpwuid(os.getuid()).pw_name
STEAMCMD_DIR = settings.system.downloader.get('steamcmd_path') or pwd.getpwuid(os.getuid()).pw_name + "/Steam/"
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
    url_download(STEAMCMD_DIR,(STEAMCMD_IRL,"steamcmd_linux.tar.gz","tar"))


def download(path,args):
  """ downloads a game via steamcmd"""
  print("omg")
  Steam_AppID, target_dir, steam_anonymous_login_possible = *args
  # check to see if steamcmd exists
  print("lol")
  install_steamcmd()

  # run steamcmd
  if steam_anonymous_login_possible == True:
    print("Running SteamCMD")
    proc_list = [STEAMCMD_EXE,"+login","anonymous","+force_install_dir",target_dir,"+app_update",str(Steam_AppID),"+quit"]
    if validate == True:
      proc_list.insert(-1,"validate")
    else:
      sp.call(proc_list)
  else:
    print("no support for normal SteamCMD logins yet.")

def getpathifexists(module,args):
  """Check if a path for the download is already in the database and if so return it else return None"""
  print("wee omg")
  sargs=",".join(str(a) for a in args)
  print(sargs)
  with open(DB_PATH,'r') as f:
    for line in f:
      lmodule,largs,llocation,ldate,lactive=line.split()
      if int(lactive) and lmodule==module and largs==sargs:
        return llocation
  print("omg")
  return None


def getfilter(active=None,Steam_AppID=None,sort="version"):
  filterfn=_true
  sortfn=None
  if Steam_AppID!=None:
    import re
    try:
      Steam_AppID=re.compile(Steam_AppID).match
    except TypeError:
      pass
  if active!=None:
    active=bool(active)
    if Steam_AppID!=None:
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive #and url(largs[0])
    else:
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive
  elif Steam_AppID!=None:    
    filterfn=lambda lmodule,largs,llocation,ldate,lactive: #url(largs[0])
  if sort == "date":
    sortfn=lambda lmodule,largs,llocation,ldate,lactive: date
  else:
    raise DownloaderError("Unknown sort key")
  return filterfn,sortfn




def _true(*arg):
  return True
