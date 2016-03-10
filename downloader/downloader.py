""" Module to download game servers and cache and share the downloads"""
from importlib import import_module
import os
import time
import random
import sys
import pwd
from urllib.parse import quote,unquote
from utils.settings import settings

# NONE OF THESE PATHS SHOULD BE ON A NFS!
# If they are there may be race conditions and database corruption

USER=settings.system.downloader['user'] # required
DB_PATH=settings.system.downloader.get('db_path') or os.path.join(pwd.getpwnam(USER).pw_dir,"downloads/downloads.txt")
TARGET_PATH=settings.system.downloader.get('target_path') or os.path.join(pwd.getpwnam(USER).pw_dir,"downloads/downloads")

DOWNLOADERS_PACKAGE = settings.system.downloader.get('downloaders_package',"downloadermodules.")
UPDATE_SUFFIX=".new"
LOCK_SUFFIX=".lock"

LOCK_PATH = DB_PATH+LOCK_SUFFIX
UPDATE_PATH = DB_PATH+UPDATE_SUFFIX

PARENTLEN=settings.system.downloader.getsection('pathgen').get('parentlen',1)
PARENTCHARS=settings.system.downloader.getsection('pathgen').get('parentchars',"abcdefghijklmnopqrstuvxyz")

DIRLEN=settings.system.downloader.getsection('pathgen').get('dirlen',8)
DIRCHARS=settings.system.downloader.getsection('pathgen').get('dirchars',"abcdefghijklmnopqrstuvwxyz0123456789_")

MAX_TRIES=settings.system.downloader.getsection('pathgen').get('maxtries',238328)

__all__=["DownloaderError",'getpath','getpathifexists','main','getpaths','getargsforpath']

class DownloaderError(Exception):
  """ An error thrown when attempting to perform a download """
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
  """Generate a new (not previously existing) path within TARGET_PATH. Returns None if no path can be generated"""
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
  """Actually do a download.
     
     Returns the path that the download was downloaded to.
     This function locates and imports the module requested then delegates to that for the actual download.
     Should only by run while the DB lock is help.
     """
  path = generatepath()
  if path is None:
    raise DownloaderError("Can't generate storage path. Clear out unused paths from the database")
  mod=_findmodule(module)
  mod.download(path,args)
  return path

def getpathifexists(module,args):
  """Check if a path for the download is already in the database and if so return it else return None"""
  sargs=",".join(quote(a) for a in args)
  with open(DB_PATH,'r') as f:
    for line in f:
      lmodule,largs,llocation,ldate,lactive=line.split()
      if int(lactive) and lmodule==module and largs==sargs:
        return llocation
  return None

def getpath(module,args):
  """Get the path for a download, downloading it if it isn't already downloaded.
     
     Can be run as any user and will change user to the download systems owner if it needs downloading"""
  path=getpathifexists(module,args)
  if path is not None:
    return path
  
  if os.getuid() != pwd.getpwnam(USER).pw_uid:
    import subprocess as sp
    try:
      path=sp.check_output(["sudo","-Hu",str(USER),os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(os.path.abspath(__file__)))),"alphagsm-downloads"),module]+list(args))
    except sp.CalledProcessError as ex:
      raise DownloaderError("Error downloading file",ret=ex.returncode)
    else:
      return unquote(path.decode(sys.stdout.encoding).strip())
  
  # Definitely running as correct user now and file not found (yet) but may have other threads updating the file so lock then check again

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
  
    sargs=",".join(quote(a) for a in args)
 
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

def _true(*arg):
  return True

def _getallfilter(active=None,sort=None):
  """a default filter that applies to any download module"""
  filterfn=_true
  sortfn=None
  if active!=None:
    active=bool(active)
    filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive
  if sort == "date":
    sortfn=lambda lmodule,largs,llocation,ldate,lactive: ldate
  else:
    raise DownloaderError("Unknown sort key")

def getpaths(module,sort=None,**filter):
  """get all paths for the given module that match a specified filter, optionally sorted.
     
     The complete list of filters available is module dependant. If module is None then the
     only valid filter is active=True/False/None which filters on the active state and the only
     valid sort order is 'date'. The module's filter function is called 'getfilter' and should
     document the valid filters and sort orders.

     The result is a list of tuples that contains the elements: 
         (module_name,[list,of,arguments],path,date_added,is_active)
     """
  if module is None:
    filterfn,sortfn=_getallfilter(**kwargs)
  else:
    filterfn,sortfn=_findmodule(module).getfilter(**kwargs)
  downloads=[]
  with open(DB_PATH,'r') as f:
    for line in f:
      lmodule,largs,llocation,ldate,lactive=line.split()
      largs=[unquote(arg) for arg in largs.split(",")]
      if (module is None or lmodule==module) and filterfn(lmodule,largs,llocation,ldate,lactive):
        downloads.append((lmodule,largs,llocation,ldate,lactive))
  if sortfn:
    downloads.sort(key=sortfn)
  return downloads

def getargsforpath(path):
  """Get the module and arguments for a download path or return None if not a valid path"""
  with open(DB_PATH,'r') as f:
    for line in f:
      lmodule,largs,llocation,ldate,lactive=line.split()
      if llocation==path:
        return(lmodule,[unquote(arg) for arg in largs.split(",")])
  return None
  
