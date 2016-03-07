#todo 

import settings_local
import downloadermodules.url as urlextra

# check if steamcmd exists, if not download it and install it via wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
# execute steamcmd/steamcmd.sh
# <user> = Anonymous by default
# ./steamcmd +login <user> +force_install_dir <download_location> +app_update <appid> +quit

def install_steamcmd():
  install_dir = settings_local.ROOT_DIR + "steamcmd/"
  url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
  
  urlextra.download(path,url,"steamcmd")
