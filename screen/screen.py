import subprocess as sp
import os

SESSIONTAG="sam#"

class ScreenError(Exception):
  pass

def start_screen(name,command,cwd=None):
  if not os.path.isdir(os.path.expanduser("~/.samlogs")):
    try:
      os.mkdir(os.path.expanduser("~/.samlogs"))
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
    sp.check_call(["screen","-rS",SESSIONTAG+name],shell=False)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen Failed with return value: "+str(ex.returncode),ex.returncode)


def logpath(name):
  return os.path.join(os.path.expanduser("~/.samlogs"),SESSIONTAG+name+".log")

__all__=["ScreenError","start_screen","send_to_screen","send_to_server","check_screen_exists","connect_to_screen","logpath"]
