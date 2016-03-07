import os
import urllib.request
import json
import time
import datetime
import subprocess as sp
from server import ServerError
import re
import screen
import downloader
import utils.updatefs
from utils.cmdparse.cmdspec import CmdSpec,OptSpec,ArgSpec
from downloadermodules import steamcmd

commands=()
command_args={"setup":CmdSpec(optionalarguments=(ArgSpec("PORT","The port for the server to listen on",int),ArgSpec("DIR","The Directory to install minecraft in",str),))}

command_descriptions={}
command_functions={} # will have elements added as the functions are defined

# Team Fortress 2 is probably the most simple example of a steamcmd game
def configure(server,port=None,dir=None,*,login="Anonymous"):
  server.data["AppID"] = 232250

  if dir is None:
    if "dir" in server.data and server.data["dir"] is not None:
      dir=server.data["dir"]
    else:
      dir=os.path.expanduser(os.path.join("~",server.name))
    if ask:
      inp=input("Where would you like to install the tf2 server: ["+dir+"] ").strip()
      if inp!="":
        dir=inp
  server.data["dir"]=dir

  if not "exe_name" in server.data:
    server.data["exe_name"] = "srcds_linux"
  server.data.save()

  return (),{"eula":eula}
  


def install(server,*,login="Anonymous"):
  if not os.path.isdir(server.data["dir"]):
    os.makedirs(server.data["dir"])

  steamcmd.install_steamcmd()
    
  # insert some cleaver means of checking if it is downloaded already or not

  
