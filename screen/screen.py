import subprocess as sp
import os
import re

SESSIONTAG="AlphaGSM#"

class ScreenError(Exception):
  pass

def start_screen(name,command,cwd=None):
  if not os.path.isdir(os.path.expanduser("~/.alphagsm/logs")):
    try:
      os.makedirs(os.path.expanduser("~/.alphagsm/logs"))
    except OSError as ex:
      raise ScreenError("Log dir doesn't exist and can't create it",ex.args)
  extraargs={}
  if cwd is not None:
    extraargs["cwd"]=cwd
  try:
    out=sp.check_output(["screen","-dmLS",SESSIONTAG+name,"-c",os.path.join(os.path.abspath(os.path.dirname(__file__)),"screenrc")]+list(command),stderr=sp.STDOUT,shell=False,**extraargs)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen failed with return value: "+str(ex.returncode)+" and output: '"+ex.output+"'",ex.returncode,ex.output)
  except FileNotFoundError as ex:
    raise ScreenError("Can't change to directory '"+cwd+"' while starting screen",ex)
  else:
    return out

def send_to_screen(name,command):
  try:
    out=sp.check_output(["screen","-S",SESSIONTAG+name,"-p","0","-X"]+list(command),stderr=sp.STDOUT,shell=False)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen failed with return value: "+str(ex.returncode)+" and output: '"+ex.output.decode()+"'",ex.returncode,ex.output)
  else:
    return out

def send_to_server(name,inp):
  return send_to_screen(name,["stuff",inp])

def check_screen_exists(name):
  try:
    send_to_screen(name,["select","."])
    return True
  except ScreenError:
    return False

def connect_to_screen(name):
  try:
    sp.check_call(["script","/dev/null","-c","screen -rS '"+SESSIONTAG+name+"'"],shell=False)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen Failed with return value: "+str(ex.returncode),ex.returncode)

def list_all_screens():
  import pwd
  curruser=pwd.getpwuid(os.getuid())[0]
  filepat=re.compile(r"\d+\."+re.escape(SESSIONTAG)+"(.*)$")
  for path,dirs,files in os.walk("/var/run/screen/"):
    user=os.path.split(path)[1]
    if user[:2] != "S-":
      continue
    user=user[2:]
    for f in files:
      match=filepat.match(f)
      if match is not None:
        if user==curruser:
          yield match.group(1)
        else:
          yield user+"/"+match.group(1)


def logpath(name):
  return os.path.join(os.path.expanduser("~/.samlogs"),SESSIONTAG+name+".log")

__all__=["ScreenError","start_screen","send_to_screen","send_to_server","check_screen_exists","connect_to_screen","list_all_screens","logpath"]
