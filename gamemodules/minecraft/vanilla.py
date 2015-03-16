import os
import urllib.request
import json
import subprocess as sp
from server import ServerError
import re
import screen

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
command_args={"setup":([],[("PORT","The port for the server to listen on",int),("DIR","The Directory to install minecraft in",str)],False,
                       [("v",["version"],"Version of minecraft to download. Overriden by the url option","version","VERSION",str),
                        ("u",["url"],"Url to download minecraft from. See https://minecraft.net/download for latest download.","url","URL",str),
                        ("l",["eula"],"Mark the eula as read","eula",None,True)]),
              "op":([("USER","The user[s] to op",str)],[],True,[]),
              "deop":([("USER","The user[s] to deop",str)],[],True,[]),
              "message":([],[("TARGET","The user[s] to send the message to. Sends to all if none given.",str)],True,[("p",["parse"],"Parse the message for selectors (otherwise prints directly).","parse",None,True)])}
command_descriptions={}
command_functions={} # will have elements added as the functions are defined

def configure(server,ask,*,port=None,dir=None,eula=None,version=None,url=None,check_versions=True,exe_name="minecraft_server.jar",download_name="minecraft_server.jar"):
  if port is None and "port" in server.data:
    port=server.data["port"]
  if port is None and not ask:
    raise ValueError("No Port and not asking")
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

  allversions=[]
  latest=None
  if check_versions:
    try:
      versionsfile=urllib.request.urlopen("https://s3.amazonaws.com/Minecraft.Download/versions/versions.json")
      versions=json.loads(versionsfile.readall().decode("utf-8"))
      latest=versions["latest"]["release"]
      allversions=[v["id"] for v in versions["versions"] if v["type"] in ["release","snapshot"]] #ditch other types as don't have servers
    except Exception as ex:
      print("Error downloading list of versions: "+str(ex)+"\nlisting versions and latest version will fail")

  

  if version is None and url is None:
    if "version" in server.data:
      version=server.data["version"]
    else:
      version="latest:"+str(latest)
    if ask:
      while True:
        inp=input("Please specify the version of minecraft to use.\nEnter \"latest\" for the latest version ("+str(latest)+
                  "), \"None\" for a custom download url or \"list\" to get a list of versions\n: ["+str(version)+"] ").strip()
        if inp.lower() == "list":
          print("'"+"', '".join(allversions)+"'")
          continue
        elif inp.lower()=="none":
          version=None
        elif inp.lower()=="latest":
          version=latest
        elif inp!="":
          version=inp
        if version is not None and version not in allversions:
          if input(version+" is not in the list of versions. Use anyway? (y/yes or n/no): ").strip().lower() not in ("y","yes"):
            continue
        break
  server.data["version"]=version

  if version is not None:
    url="https://s3.amazonaws.com/Minecraft.Download/versions/"+version+"/minecraft_server."+version+".jar"

  if url is None:
    if "url" in server.data and server.data["url"] is not None:
      url=server.data["url"]
    else:
      url="https://s3.amazonaws.com/Minecraft.Download/versions/1.8.3/minecraft_server.1.8.3.jar"
    if ask:
      inp=input("Please give the download url for the minecraft server:\n["+url+"]\n ").strip()
      if inp!="":
        url=inp
  server.data["url"]=url

  if eula is None:
    if ask:
      eula=input("Please confirm you have read the eula (y/yes or n/no): ").strip().lower() in ("y","yes")
    else:
      eula=False

  server.data["exe_name"] = exe_name
  server.data["download_name"] = download_name
  server.data.save()

  return (),{"eula":eula}

#def install(server,*,eula=False,):
def install(server,*,eula=False):
  if not os.path.isdir(server.data["dir"]):
    os.makedirs(server.data["dir"])
  mcjar=os.path.join(server.data["dir"],server.data["exe_name"])
  mcdwl=os.path.join(server.data["dir"],server.data["download_name"])

  # if URL has changed, or the executable does not exist, redownload the server
  if "current_url" not in server.data or server.data["current_url"]!=server.data["url"] or not os.path.isfile(mcjar):
    try:
      fname,headers=urllib.request.URLopener().retrieve(server.data["url"],filename=mcdwl)
      print("Downloading Server Files")
    except urllib.error.URLError as ex:
      print("Error downloading "+ server.data["exe_name"] + ": "+ex.reason)
      raise ServerError("Error setting up server. Server file isn't already downloaded and can't download requested version")
    print(fname)
    print(headers)
    server.data["current_url"]=server.data["url"]
  else:
    print("Skipping download")

  # probably need to extract the executable from ... something
  download_url, download_extension = os.path.splitext(server.data["current_url"])
  print(download_extension)
  if not os.path.isfile(mcjar) and download_extension == ".zip":
    cmd = ["unzip","-d",server.data["dir"],"-o",mcdwl]
    print("Unpacking Server Files")
    print(cmd)
    print(server.data["dir"])
    print(mcdwl)
    sp.check_output(cmd,shell=False)
  
  eulafile=os.path.join(server.data["dir"],"eula.txt")
  if not os.path.isfile(eulafile): # use as flag for has the server created it's files
    print("Starting server to create settings")
    try:
      ret=sp.check_call(["java","-jar",server.data["exe_name"],"nogui"],cwd=server.data["dir"],shell=False,timeout=10)
    except sp.CalledProcessError as ex:
      +-  print("Error running server. Java returned status: "+ex.returncode)
    except sp.TimeoutExpired as ex:
      print("Error running server. Process didn't complete in time")
  if eula and os.path.isfile(eulafile):
    updateconfig(eulafile,{"eula":"true"})
  updateconfig(os.path.join(server.data["dir"],"server.properties"),{"server-port":str(server.data["port"])})
  server.data.save()
    
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
  raise ServerError("All read only as not yet implemented")

def backup(server):
  print("Not yet implemented")

def op(server,*users):
  for user in users:
    screen.send_to_server(server.name,"\nop "+user+"\n")
command_functions["op"]=op

def deop(server,*users):
  for user in users:
    screen.send_to_server(server.name,"\ndeop "+user+"\n")
command_functions["deop"]=deop

