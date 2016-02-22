from importlib import import_module
import os
import time
import random
import sys

# NONE OF THESE PATHS SHOULD BE ON A NFS!
# If they are there may be race conditions and database corruption

DB_PATH="/home/alphagsm/downloads/downloads.txt"
UPDATE_SUFFIX=".new"
TARGET_PATH="/home/alphagsm/downloads/downloads"
LOCK_SUFFIX=".lock"
USER=1036

PARENTLEN=1
PARENTCHARS="abcdefghijklmnopqrstuvxyz"

DIRLEN=8
DIRCHARS="abcdefghijklmnopqrstuvwxyz0123456789_"

MAX_TRIES=238328

LOCK_PATH = DB_PATH+LOCK_SUFFIX
UPDATE_PATH = DB_PATH+UPDATE_SUFFIX

DOWNLOADERS_PACKAGE = "downloadermodules."

__all__=["DownloaderError",'getpath','getpathifexists','main']

class DownloaderError(Exception):
  def __init__(self,msg,*args,ret=1,**kwargs):
    super(DownloaderError,self).__init__(msg,*args,**kwargs)
    self.ret=ret

def _findmodule(name):
  while True:
    name=str(name)
    if len(name)<2 and all((len(el)>0 and el.isalnum()) for el in name.split(".")):
      raise DownloaderError("Invalid module requested: "+self.data["module"])
    try:
      module=import_module(DOWNLOADERS_PACKAGE+name)
    except ImportError as ex:
      raise DownloaderError("Can't find module: "+name,ex)
    if not hasattr(module,'__file__'): # no filesystem path so must be a namespace path
      name=name+".DEFAULT"
      continue
    try:
      name=module.ALIAS_TARGET
    except AttributeError:
      return module


def generatepath():
  rnd=random.Random()
  # choose a destination path
  dirn=os.path.join(TARGET_PATH,"".join(rnd.choice(PARENTCHARS) for i in range(PARENTLEN)))
  if not os.path.isdir(dirn):
    try:
      os.mkdir(dirn, 0o755)
    except FileExistsError:
      pass

  for seq in range(MAX_TRIES):
    path = os.path.join(dirn, "".join(rnd.choice(DIRCHARS) for i in range(DIRLEN)))
    try:
      os.mkdir(path, 0o755)
      return path
    except FileExistsError:
      continue    # try again
  return None

# This will always run while the DB is locked
def download(module,args):
  path = generatepath()
  if path is None:
    raise DownloaderError("Can't generate storage path. Clear out unused paths from the database")
  mod=_findmodule(module)
  mod.download(path,args)
  return path

def getpathifexists(module,args):
  sargs=",".join(args)
  with open(DB_PATH,'r') as f:
    for line in f:
      lmodule,largs,llocation,ldate,lactive=line.split()
      if int(lactive) and lmodule==module and largs==sargs:
        return llocation
  return None

def getpath(module,args):
  path=getpathifexists(module,args)
  if path is not None:
    return path
  
  if os.getuid() != USER:
    import subprocess as sp
    try:
      path=sp.check_output(["sudo","-Hu","#"+str(USER),os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(os.path.abspath(__file__)))),"alphagsm-downloads"),module]+list(args))
    except sp.CalledProcessError as ex:
      raise DownloaderError("Error downloading file",ret=ex.returncode)
    else:
      return path.decode(sys.stdout.encoding).strip()
  
  # Definitely running as correct user now and file now found (yet) but may have other threads updating the file so lock then check again

  while True:
    try:
      open(LOCK_PATH,"x")
    except FileExistsError:
      time.sleep(1)
      continue
    else:
      break
  try:  
    # Now locked so no-one else can be changing it
    path=getpathifexists(module,args)
    if path is not None:
      return Path
    
    # definitely doesn't exist so we need to download it
    path=download(module,args)
  
    sargs=",".join(args)
 
    try:
      os.remove(UPDATE_PATH)
    except FileNotFoundError:
      pass 
    with open(UPDATE_PATH,'w') as f:
      with open(DB_PATH,"r") as f2:
        for l in f2:
          f.write(l)
      f.write(" ".join((module,sargs,path,str(time.time()),str(1)))+"\n")
    os.rename(UPDATE_PATH,DB_PATH)
    return path
  finally:
    os.remove(LOCK_PATH)
  
main=getpath  
  
  

