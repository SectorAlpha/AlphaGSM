from downloader import DownloaderError
import urllib.request
import os.path
import subprocess as sp
import sys

def reporthook(blocknum, blocksize, totalsize):
  readsofar = blocknum * blocksize
  if totalsize > 0:
    if readsofar > totalsize:
      readsofar = totalsize
    percent = readsofar * 1e2 / totalsize
    print("\r%5.1f%% %*d / %d" % (
        percent, len(str(totalsize)), readsofar, totalsize),end='')
  else: # total size is unknown
    print("read %d" % (readsofar,))
  tenth=int(10*readsofar/totalsize)*totalsize/10
  if tenth<=readsofar and readsofar<tenth+blocksize:
    print()

def download(path,args):
  url,targetname,*args=args
  targetname=os.path.join(path,targetname)
  decompress=None
  if len(args)>1:
    raise DownloaderError("Too many arguments")
  elif len(args)==1:
    decompress=args[0]
    if decompress not in ["zip","tar","gz","tgz"]:
      raise DownloaderError("Unknown decompression type")
    if decompress in ["gz"]: # compression without filenames
      targetname+="."+decompress
  try:
    fname,headers=urllib.request.urlretrieve(url,filename=targetname,reporthook=reporthook)
  except urllib.error.URLError as ex:
    print("Error downloading "+str(targetname)+": "+ex.reason)
    raise DownloaderError("Can't download file")
  if decompress == "zip":
    ret=sp.call(["unzip",targetname,"-d",path],stdout=sys.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")
  elif decompress == "tar":
    ret=sp.call(["tar","-xf",targetname,"-C",path],stdout=sys.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")
  elif decompress == "tgz":
    ret=sp.call(["tar","-xfz",targetname,"-C",path],stdout=sys.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")
  elif decompress == "gz":
    ret=sp.call(["gunzip",targetname],stdout=sys.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")

def _true(*arg):
  return True
  
def getallfilter(active=None,url=None,compression=None,sort=None):
  filterfn=_true
  sortfn=None
  if url!=None:
    import re
    try:
      url=re.compile(url).match
    except TypeError:
      pass
  if active!=None:
    active=bool(active)
    if url!=None:
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: return active == lactive and url(largs[0])
    else:
      filterfn=lambda lmodule,largs,llocation,ldate,lactive: return active == lactive
  elif url!=None:    
    filterfn=lambda lmodule,largs,llocation,ldate,lactive: return url(largs[0])
  if sort == "date":
    sortfn=lambda lmodule,largs,llocation,ldate,lactive: return date
  else:
    raise DownloaderError("Unknown sort key")
 
