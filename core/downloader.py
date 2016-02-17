from importlib import import_module
import os
import time
import random

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
    return None 
  mod=import_module(module)
  if mod.download(path,args):
    return path
  else:
    return None

def getpathifexists(module,args):
  sargs=",".join(args)
  with open(DB_PATH,'r') as f:
    for line in f:
      lmodule,largs,llocation,ldate,lactive=line.split()
      if lactive and lmodule==module and largs==sargs:
        print(llocation)
        return True
  return False

def getpath(module,args):
  print(module,args)
  if getpathifexists(module,args):
    return 0
  
  if os.getuid() != USER:
    import subprocess as sp
    ret=sp.call(["sudo","-Hu","#"+str(USER),os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(os.path.abspath(__file__)))),"alphagsm-downloads"),module]+args)
    return ret
  
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
    if getpathifexists(module,args):
      return 0
    
    # definitely doesn't exist so we need to download it
    path=download(module,args)
  
    # Nothing available
    if path is None:
      return 1
  
    print(path)
  
    sargs=",".join(args)
 
    try:
      os.remove(UPDATE_PATH)
    except FileNotFoundError:
      pass 
    with open(UPDATE_PATH,'w') as f:
      with open(DB_PATH,"r") as f2:
        for l in f2:
          f.write(l)
      f.write(" ".join(lmodule,largs,llocation,ldate,lactive)+"\n")
    os.rename(UPDATE_PATH,DB_PATH)
  finally:
    os.remove(LOCK_PATH)
  return 0
  
main=getpath  
  
  

