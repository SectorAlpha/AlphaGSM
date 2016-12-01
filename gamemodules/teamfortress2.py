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
from utils import backups
from utils import updatefs
import random

import utils.steamcmd as steamcmd

steam_app_id = 232250
steam_anonymous_login_possible = True

commands=()
command_args={"setup":CmdSpec(optionalarguments=(ArgSpec("PORT","The port for the server to listen on",int),ArgSpec("DIR","The Directory to install minecraft in",str),))}

# required still
command_descriptions={}
command_functions={} # will have elements added as the functions are defined

# example tf2 runscript ./srcds_run -game tf -port 27015 +maxplayers 32 +map cp_dustbowl"

# Team Fortress 2 is probably the most simple example of a steamcmd game
def configure(server,ask,port=None,dir=None,*,exe_name="srcds_run"):
  """
  This function creates the configuration details for the  server
  
  inputs:
    server: the server object
    ask: whether to request details (e.g port) from the user
    dir: the server installation dir
    *: other keyword arguments
    eula: whether the user agrees to sign the eula
    exe_name: the executable name of the server
  """


  server.data["Steam_AppID"] = steam_app_id
  server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible

  # do we have backup data already? if not initialise the dictionary
  if 'backup' not in server.data:
    server.data['backup']={}
  if 'profiles' not in server.data['backup']:
    server.data['backup']['profiles']={}
  # if no backup profile exists, create a basic one
  if len(server.data['backup']['profiles'])==0:
    # essentially, the world, server properties and the root level json files are the best ones to back up. This can be configured though in the backup setup
    server.data['backup']['profiles']['default']={'targets':{}}
  if 'schedule' not in server.data['backup']:
    server.data['backup']['schedule']=[]
  if len(server.data['backup']['schedule'])==0:
    # if default does not exist, create it
    profile='default'
    if profile not in server.data['backup']['profiles']:
      profile=next(iter(server.data['backup']['profiles']))
    # set the default to never back up
    server.data['backup']['schedule'].append((profile,0,'days'))

  # assign the port to the server
  if port is None and "port" in server.data:
    port=server.data["port"]
  if ask:
    while True:
      inp=input("Please specify the port to use for this server: "+(str(port) if port is not None else "")).strip()
      if port is not None and inp == "":
        break
      try:
        port=int(inp)
      except ValueError as v:
        print(inp+" isn't a valid port number")
        continue
      break
  if port is None :
    raise ValueError("No Port")
  server.data["port"]=port

  # assign install dir for the server
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

  # if exe_name is not asigned, use the function default one
  if not "exe_name" in server.data:
    server.data["exe_name"] = "srcds_linux"
  server.data.save()

  return (),{}
  

def install(server):
  doinstall(server)
  #TODO: any config files that need creating or any commands that need running before the server can start for the first time


def doinstall(server):
  """ Do the installation of the latest version. Will be called by both the install function thats part of the setup command and by the auto updater """
  if not os.path.isdir(server.data["dir"]):
    os.makedirs(server.data["dir"])

  steamcmd.download(server.data["dir"],server.data["Steam_AppID"],server.data["Steam_anonymous_login_possible"],validate=True)

def get_start_command(server):
# example run ./srcds_run -game tf -port 27015 +maxplayers 32 +map cf_2fort
  return [server.data["exe_name"],"-game","tf","-port",str(server.data["port"]),"+maxplayers","16","+map","cp_dustbowl"],server.data["dir"]

def do_stop(server,j):
  screen.send_to_server(server.name,"\nstop\n")

def stop(self,*args,**kwargs):
  """Stop the server. If the server can't be stopped even after multiple attempts then raises a ServerError"""
  if not screen.check_screen_exists(self.name):
    raise ServerError("Error: Can't stop a server that isn't running")
  jmax=5
  try:
    jmax=min(jmax,self.module.max_stop_wait)
  except AttributeError:
    pass
  print("Will try and stop server for "+str(jmax)+" minutes")
  for j in range(jmax):
    self.module.do_stop(self,j,*args,**kwargs)
    for i in range(6):
      if not screen.check_screen_exists(self.name):
        return # session doesn't exist so success
      time.sleep(10)
    if not screen.check_screen_exists(self.name):
      return
    print("Server isn't stopping after "+str(j+1)+" minutes")
  print("Killing Server")
  screen.send_to_screen(self.name,["stop"])
  time.sleep(1)
  if screen.check_screen_exists(self.name):
    raise ServerError("Error can't kill server")

def status(server,verbose):
  pass


## TODO integrate Steam games properly into the downloads module.
##
##
##def doinstall(server):
##  """# Do the installation of the latest version. Will be called by both the install function thats part of the setup command and by the auto updater """
##  if not os.path.isdir(server.data["dir"]):
##    os.makedirs(server.data["dir"])
##
##  # crashes here.. what is this? AppID:server.data["Steam_AppID"]
##  versions=downloader.getpaths("steamcmd",sort="version",active=True)
##  versions = []
##
##  if len(versions)==0:
##    server.data["version"]=1
##    path=downloader.getpath("steamcmd",(server.data["Steam_AppID"],server.data["dir"],server.data["Steam_anonymous_login_possible"]))
##  else:
##    latest=versions[0]
##    server.data["version"]=latest[1][0]
##    path=latest[2]
##
##  basetagpath=os.path.join(server.data["dir"],".~basetag")
##  try:
##    oldpath=os.readlink(basetagpath)
##  except FileNotFoundError:
##   oldpath="/dev/null/INVALID"
##  if oldpath==path:
##    if update:
##      print("Latest version already downloaded")
##      return
##
##  # for a future release
##  # server.data["version"]+=1;
##
##    path=downloader.getpath("steamcmd",(server.data["Steam_AppID"],server.data["dir"],server.data["Steam_anonymous_login_possible"]))
##    # should now be different as this shouldn't (assuming downloader is working right) return the same path as it did for the old version
##  server.data.save()
##  os.remove(basetagpath)
##  updatefs.update(oldpath,path,server.data["dir"]) #TODO: Fill in the skip, linkdir and copy args
##  os.symlink(downloadpath,basetagpath)


  


