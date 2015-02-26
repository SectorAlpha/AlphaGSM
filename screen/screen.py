import subprocess as sp
import os

SESSIONTAG="sam#"

class ScreenError(Exception):
  pass

def startScreen(name,command):
  if not os.path.isdir(os.path.expanduser("~/.samlogs")):
    try:
      os.mkdir(os.path.expanduser("~/.samlogs"))
    except OSError as ex:
      raise ScreenError("Log dir doesn't exist and can't create it",ex.args)
  try:
    out=sp.check_output(["screen","-dmLS",SESSIONTAG+name,"-c",os.path.join(os.path.abspath(os.path.dirname(__file__)),"screenrc")]+list(command),stderr=sp.STDOUT,shell=False)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen failed with return value: "+str(ex.returncode)+" and output: '"+ex.output+"'",ex.returncode,ex.output)
  else:
    return out

def sendToScreen(name,command):
  try:
    out=sp.check_output(["screen","-S",SESSIONTAG+name,"-p","0","-X"]+list(command),stderr=sp.STDOUT,shell=False)
  except sp.CalledProcessError as ex:
    raise ScreenError("Screen failed with return value: "+str(ex.returncode)+" and output: '"+ex.output+"'",ex.returncode,ex.output)
  else:
    return out

def sendToServer(name,inp):
  return sendtoscreen(name,["stuff",inp])


__all__=["ScreenError","startScreen","sendToScreen","sendToServer"]
