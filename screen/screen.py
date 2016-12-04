import subprocess as sp
import os
import re
from utils.settings import settings

SESSIONTAG=settings.system.getsection('screen').get('sessiontag','AlphaGSM#')
LOGPATH=os.path.expanduser(settings.user.getsection('screen').get('screenlog_path',"~/.alphagsm/conf"))
try:
  KEEPLOGS=int(setting.user.getsection('screen').get('keeplogs',5))
except:
  KEEPLOGS=5

class ScreenError(Exception):
  pass

def rotatelogs(dirn,name):
  if not os.path.exists(os.path.join(dirn,name)):
    return
  match=name+"."
  length=len(match)
  logs=[(int(el[length:]),el) for el in os.listdir(dirn) if el[:length]==match and el[length:].isdigit()]
  logs.sort()
  logs=[(i,1 if i==j else 0,f) for j,(i,f) in enumerate(logs)] 
  oldlogs=(f for i,j,f in logs if i+j>= KEEPLOGS)
  for f in oldlogs:
    os.remove(os.path.join(dirn,f))
  logstoshift=[(i,f) for i,j,f in logs if j==1 and i+j < KEEPLOGS]
  # only care if logs are in order and start correctly with index 0
  for i,f in reversed(logstoshift):
    os.rename(os.path.join(dirn,f),os.path.join(dirn,match+str(i+1)))
  os.rename(os.path.join(dirn,name),os.path.join(dirn,name+".0"))

def start_screen(name,command,cwd=None):
  """
  Function to start a screen session. 
  Note: this will throw if for any reason it can't start the request screen session 
    (it already exists or screen is unavailable or something) but will succeed 
    even if the program to run inside of screen is invalid in which case the session 
    will immediately shut down again.

  If you need to ensure the session started successfully try waiting a short amount 
  of time (1s say) and then check if the screen session exists.
  """
  if not os.path.isdir(os.path.expanduser("~/.alphagsm/logs")):
    try:
      os.makedirs(os.path.expanduser("~/.alphagsm/logs"))
    except OSError as ex:
      raise ScreenError("Log dir doesn't exist and can't create it",ex.args)
  rotatelogs(os.path.expanduser("~./alphagsm/logs"),SESSIONTAG+name+".log")
  extraargs={}
  if cwd is not None:
    extraargs["cwd"]=cwd
  try:
    out=sp.check_output(["screen","-dmLS",SESSIONTAG+name,"-c",os.path.join(os.path.abspath(os.path.dirname(__file__)),"screenrc")]+list(command),stderr=sp.STDOUT,shell=False,**extraargs)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen failed with return value: "+str(ex.returncode)+" and output: '"+ex.output+"'",ex.returncode,ex.output)
  except FileNotFoundError as ex:
    raise ScreenError("Can't change to directory '"+cwd+"' while starting screen",ex)
  except OSError as ex:
    raise ScreenError("Error executing screen: "+str(ex))
  else:
    # returning.
    return out

def send_to_screen(name,command):
  try:
    out=sp.check_output(["screen","-S",SESSIONTAG+name,"-p","0","-X"]+list(command),stderr=sp.STDOUT,shell=False)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen failed with return value: "+str(ex.returncode)+" and output: '"+ex.output.decode()+"'",ex.returncode,ex.output)
  except OSError as ex:
    raise ScreenError("Error executing screen: "+str(ex))
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
  except OSError as ex:
    raise ScreenError("Error executing screen: "+str(ex))

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
