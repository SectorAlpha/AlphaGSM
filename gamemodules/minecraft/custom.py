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

_confpat=re.compile(r"\s*([^ \t\n\r\f\v#]\S*)\s*=(?:\s*(\S+))?(\s*)\Z")
def updateconfig(filename,settings):
  lines=[]
  if os.path.isfile(filename):
    settings=settings.copy()
    with open(filename,"r") as f:
      for l in f:
        m=_confpat.match(l)
        if m is not None and m.group(1) in settings:
          lines.append(m.expand(r"\1="+settings[m.group(1)]+r"\3"))
          del settings[m.group(1)]
        else:
          lines.append(l)
  for k,v in settings.items():
    lines.append(k+"="+v+"\n")
  print(lines)
  with open(filename,"w") as f:
    f.write("".join(lines))


commands=("op","deop")
command_args={"setup":CmdSpec(optionalarguments=(ArgSpec("PORT","The port for the server to listen on",int),ArgSpec("DIR","The Directory to install minecraft in",str),),
                              options=(OptSpec("l",["eula"],"Mark the eula as read","eula",None,True),)),
              "op":CmdSpec(requiredarguments=(ArgSpec("USER","The user[s] to op",str),),repeatable=True),
              "deop":CmdSpec(requiredarguments=(ArgSpec("USER","The user[s] to deop",str),),repeatable=True),
              "message":CmdSpec(optionalarguments=(ArgSpec("TARGET","The user[s] to send the message to. Sends to all if none given.",str),),repeatable=True,
                      options=(OptSpec("p",["parse"],"Parse the message for selectors (otherwise prints directly).","parse",None,True),))}
command_descriptions={}
command_functions={} # will have elements added as the functions are defined

def configure(server,ask,port=None,dir=None,*,eula=None,exe_name="minecraft_server.jar"):
  server.data['backupfiles']=['world','server.properties','whitelist.json','ops.json','banned-ips.json','banned-players.json']
  
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

  if dir is None:
    if "dir" in server.data and server.data["dir"] is not None:
      dir=server.data["dir"]
    else:
      dir=os.path.expanduser(os.path.join("~",server.name))
    if ask:
      inp=input("Where would you like to install the minecraft server: ["+dir+"] ").strip()
      if inp!="":
        dir=inp
  server.data["dir"]=dir

  if eula is None:
    if ask:
      eula=input("Please confirm you have read the eula (y/yes or n/no): ").strip().lower() in ("y","yes")
    else:
      eula=False

  if not "exe_name" in server.data:
    server.data["exe_name"] = exe_name
  server.data.save()

  return (),{"eula":eula}

def install(server,*,eula=False):
  if not os.path.isdir(server.data["dir"]):
    os.makedirs(server.data["dir"])
  mcjar=os.path.join(server.data["dir"],server.data["exe_name"])
  if not os.path.isfile(mcjar):
    raise ServerError("Can't find server jar ({}). Please place the files in the directory and/or update the 'exe_name' then run setup again".format(mcjar))
  server.data.save()

  eulafile=os.path.join(server.data["dir"],"eula.txt")
  configfile=os.path.join(server.data["dir"],"server.properties")
  if not os.path.isfile(configfile) or (eula and not os.path.isfile(eulafile)): # use as flag for has the server created it's files
    print("Starting server to create settings")
    try:
      ret=sp.check_call(["java","-jar",server.data["exe_name"],"nogui"],cwd=server.data["dir"],shell=False,timeout=20)
    except sp.CalledProcessError as ex:
      print("Error running server. Java returned status: "+ex.returncode)
    except sp.TimeoutExpired as ex:
      print("Error running server. Process didn't complete in time")
  updateconfig(configfile,{"server-port":str(server.data["port"])})
  if eula:
    updateconfig(eulafile,{"eula":"true"})
    
def get_start_command(server):
  return ["java","-jar",server.data["exe_name"],"nogui"],server.data["dir"]

def do_stop(server,j):
  screen.send_to_server(server.name,"\nstop\n")

def status(server,verbose):
  pass

def message(server,msg,*targets,parse=False):
  if len(targets)<1:
    targets=["@a"]
  if parse and "@" in msg:
    msglist=[]
    pat=re.compile(r"([^@]*[^\\])?(@.(?:\[[^\]]+\])?)")
    while True:
      match=pat.match(msg)
      if match is None:
        break
      if match.group(1) is not None:
        msglist.append(match.group(1)) # group is optional
        # nothing stopping two selectors straight after each other
      msglist.append({"selector":match.group(2)})
      msg=msg[match.end(0):]
    msglist.append(msg)
    msgjson=json.dumps(msglist)
  else:
    msgjson=json.dumps({"text":msg})
  for target in targets:
    print("tellraw "+target+" "+msgjson)
  screen.send_to_server(server.name,"\ntellraw "+target+" "+msgjson+"\n")

def checkvalue(server,key,value):
  if key == "exe_name":
    return value
  if key == "backupfiles":
    return value.split(",")
  raise ServerError("{} read only as not yet implemented".format(key))

def backup(server):
  if screen.check_screen_exists(server.name):
    screen.send_to_server(server.name,"\save-off\nsave-all\n")
    time.sleep(2)
  try:
    sp.check_call(['zip','-ry',os.path.join('backup',datetime.datetime.now().isoformat())]+server.data['backupfiles']+["-x","backup/*"],cwd=server.data['dir'])
  except sp.CalledProcessError as ex:
    print("Error backing up the server")
  if screen.check_screen_exists(server.name):
    screen.send_to_server(server.name,"\save-on\nsave-all\n")

def op(server,*users):
  for user in users:
    screen.send_to_server(server.name,"\nop "+user+"\n")
command_functions["op"]=op

def deop(server,*users):
  for user in users:
    screen.send_to_server(server.name,"\ndeop "+user+"\n")
command_functions["deop"]=deop

