#todo 

from utils.settings import settings 
from . import url as urlextra

# check if steamcmd exists, if not download it and install it via wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
# execute steamcmd/steamcmd.sh
# <user> = Anonymous by default
# ./steamcmd +login <user> +force_install_dir <download_location> +app_update <appid> +quit

def install_steamcmd():
  # only run as the downloads user so ~ will be that users home directory
  install_dir = setting.user.getsection("downloader").getsection("steamcmd").get("path",os.path.expanduser("~/steamcmd"))
  url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
  urlextra.download(install_dir,[url,"steamcmd.tgz","tgz"])

