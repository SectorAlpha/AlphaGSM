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
import random

from downloadermodules.url import download as url_download

# example tf2 runscript ./srcds_run -game tf -port 27015 +maxplayers 32 +map cp_dustbowl"

steam_app_id = 232250
steam_anonymous_login_possible = True

commands=()

command_args={"setup":CmdSpec(optionalarguments=(ArgSpec("PORT","The port for the server to listen on",int),ArgSpec("DIR","The Directory to install Team Fortress 2 in",str))),
              }

# required
command_descriptions={}

def configure(server,ask,port=None,dir=None,*,exe_name="srcds_run"):
  """
  This function creates the configuration details for the minecraft server
  
  inputs:
    server: the server object
    ask: whether to request details (e.g port) from the user
    dir: the server installation dir
    *: other keyword arguments
    eula: whether the user agrees to sign the eula
    exe_name: the executable name of the server
  """
  # do we have backup data already? if not initialise the dictionary
  if 'backup' not in server.data:
    server.data['backup']={}
  if 'profiles' not in server.data['backup']:
    server.data['backup']['profiles']={}
  # if no backup profile exists, create a basic one
  if len(server.data['backup']['profiles'])==0:
    # essentially, the world, server properties and the root level json files are the best ones to back up. This can be configured though in the backup setup
    server.data['backup']['profiles']['default']={'targets':[]}
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

  # assign the installation directory
  if dir is None:
    if "dir" in server.data and server.data["dir"] is not None:
      dir=server.data["dir"]
    else:
      # if no directory is assigned, set it to the users home area
      dir=os.path.expanduser(os.path.join("~",server.name))
    if ask:
      # set a custom location to install the directory?
      inp=input("Where would you like to install the Team Fortress 2 server: ["+dir+"] ").strip()
      if inp!="":
        dir=inp
  server.data["dir"]=dir

  # if exe_name is not asigned, use the function default one
  if not "exe_name" in server.data:
    server.data["exe_name"] = exe_name
  server.data.save()

  return (),{"steam_app_id":steam_app_id,"steam_anonymous_login_possible":steam_anonymous_login_possible}

def install(server,*,steam_app_id=None,steam_anonymous_login_possible=False):
  import inspect
  print("lol")
  print(os.path.realpath(__file__))
  print(inspect.stack()[0][1])
  print(inspect.stack()[-1][1])
  print(os.path.dirname(os.path.abspath(inspect.stack()[0][1])))
  steam_cmd_install_dir = os.path.split(os.path.dirname(os.path.abspath(inspect.stack()[0][1])))[0] #i.e gets the alphaGSM install location
  steam_cmd_install_dir = steam_cmd_install_dir + "/downloadermodules/steamcmd/"
  steam_cmd_executable = steam_cmd_install_dir + "steamcmd.sh"

  # if steamcmd dir does not exist, download it  
  if not os.path.exists(steam_cmd_install_dir):
    os.makedirs(steam_cmd_install_dir)

  if not os.path.isfile(steam_cmd_executable):
    # if steamcmd files do not exist, download it
    steam_cmd_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
    url_download(steam_cmd_install_dir,(steam_cmd_url,"steamcmd_linux.tar.gz","tar"))
  
  # run steamcmd
  if steam_anonymous_login_possible == True:
    print("running steamcmd")
    sp.call([steam_cmd_executable,"+login","anonymous","+force_install_dir",server.data["dir"],"+app_update",str(steam_app_id),"+quit"])
  else:
    print("no support for anonymous steamcmd logins yet")
  


