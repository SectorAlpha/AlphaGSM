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
                      options=(OptSpec("p",["parse"],"Parse the message for selectors (otherwise prints directly).","parse",None,True),)),
              "backup":CmdSpec(optionalarguments=(ArgSpec("PROFILE","Do a backup using the specified profile",str),))}
command_descriptions={'set':"The available keys to set are:\texe_name: (1 value) the name of the jar file to execute\n\tbackup.profiles.PROFILENAME.targets: (many values) the "
                            "targets to include in a backup using the specified profile\n\tbackup.profiles.PROFILENAME.exclusions: (many values) patterns that match files to "
                            "exclude from a backup using the specified profile\n\tbackup.profiles.PROFILENAME.base: (one value) the name of a profile that this profile extends\n\t"
                            "backups.profiles.PROFILENAME.replace_targets and backups.profiles.PROFILENAME.replace_exclusions: (one value: on/off) Should the relevent entry "
                            "replace the base rather than extend the bases value\n\tbackups.profiles.PROFILENAME.lifetime: (two values: length year,month,week,day) How long "
                            "the backups should be kept for\n\tbackups.schedule.INDEX/APPEND: (3 values: profile timelength timeunit) how long there should be between backups "
                            "using that profiles"}
command_functions={} # will have elements added as the functions are defined

def configure(server,ask,port=None,dir=None,*,eula=None,exe_name="minecraft_server.jar"):
  if 'backup' not in server.data:
    server.data['backup']={}
  if 'profiles' not in server.data['backup']:
    server.data['backup']['profiles']={}
  if len(server.data['backup'])==0:
    server.data['backup']['profiles']['default']={'targets':['world','server.properties','whitelist.json','ops.json','banned-ips.json','banned-players.json']}
  if 'schedule' not in server.data['backup']:
    server.data['schedule']=[]
  if len(server.data['schedule'])==0:
    profile='default'
    if profile not in server.data['backup']['profiles']:
      profile=next(iter(server.data['backup']['profiles']))
    server.data['backup']['schedule'].append((profile,0,'days'))
  
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
  cmd="\n".join("tellraw "+target+" "+msgjson for target in targets)
  print(cmd)
  screen.send_to_server(server.name,"\n"+cmd+"\n")

def checkvalue(server,key,*value):
  if key[0] == "TEST":
    return value[0]
  if key == ("exe_name",):
    if len(value)!=1:
      raise ServerError("Only one value supported for 'exe_name'")
    return value[0]
  if key[0] == ("backup"):
    try:
      return backups.checkdatavalue(server.data["backup"],key[1:],*value)
    except backups.BackupError as ex:
      raise ServerError(ex)
  raise ServerError("{} invalid key to set".format(".".join(str(k) for k in key)))

def backup(server,profile=None):
  if screen.check_screen_exists(server.name):
    screen.send_to_server(server.name,"\save-off\nsave-all\n")
    time.sleep(5)
  try:
    backups.backup(server.data["dir"],server.data['backup'],profile)
  except backups.BackupError as ex:
    raise ServerError("Error backing up server: {}".format(ex))
  finally:
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

