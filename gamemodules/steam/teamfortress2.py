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
from utils import updatefs

commands=()
command_args={"setup":CmdSpec(optionalarguments=(ArgSpec("PORT","The port for the server to listen on",int),ArgSpec("DIR","The Directory to install minecraft in",str),))}

command_descriptions={}
command_functions={} # will have elements added as the functions are defined

# Team Fortress 2 is probably the most simple example of a steamcmd game
def configure(server,port=None,dir=None,*):
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
  

def install(server):
  doinstall(server)
  #TODO: any config files that need creating or any commands that need running before the server can start for the first time

def doinstall(server)
  """ Do the installation of the latest version. Will be called by both the install function thats part of the setup command and by the auto updater """
  if not os.path.isdir(server.data["dir"]):
    os.makedirs(server.data["dir"])

  versions=downloader.getpaths("steamcmd",active=True,AppID=server.data["AppID"],sort="version")
  
  if len(version)==0:
    self.data["version"]=1
    path=downloader.getpath("steamcmd",server.data["version"],server.data["AppID"])
  else:
    latest=versions[0]
    self.data["version"]=latest[1][0]
    path=latest[2]

  basetagpath=os.path.join(server.data["dir"],".~basetag")
  try:
    oldpath=os.readlink(basetagpath)
  except FileNotFoundError:
    oldpath="/dev/null/INVALID"
  if oldpath==path:
    if update:
      print("Latest version already downloaded")
      return
    server.data["version"]+=1;
    path=downloader.getpath("steamcmd",server.data["version"],server.data["AppID"])
    # should now be different as this shouldn't (assuming downloader is working right) return the same path as it did for the old version
  server.data.save()
  os.remove(basetagpath)
  updatefs.update(oldpath,path,server.data["dir"]) #TODO: Fill in the skip, linkdir and copy args
  os.symlink(downloadpath,basetagpath)
   

     


  
