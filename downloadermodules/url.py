from downloader import DownloaderError
import urllib.request
import os.path
import subprocess as sp

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
    if decompres in ["gz"]: # compression without filenames
      targetname+="."+decompress
  try:
    fname,headers=urllib.request.urlretrieve(url,filename=targetname)
  except urllib.error.URLError as ex:
    print("Error downloading "+str(targetname)+": "+ex.reason)
    raise DownloaderError("Can't download file")
  if decompress is "zip":
    ret=sp.call(["unzip",targetname,"-d",path],stdout=os.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")
  elif decompress is "tar":
    ret=sp.call(["tar","-xf",targetname,"-C",path],stdout=os.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")
  elif decompress is "tgz":
    ret=sp.call(["tar","-xfz",targetname,"-C",path],stdout=os.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")
  elif decompress is "gz":
    ret=sp.call(["gunzip",targetname],stdout=os.stderr)
    if ret!=0:
      raise DownloaderError("Error extracting download")
  
  
   
