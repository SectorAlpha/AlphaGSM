"""HTTP and archive-based download helpers used by the shared downloader cache."""

from downloader import DownloaderError
import urllib.request
import os.path
import shutil
import subprocess as sp
import sys

USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"

def reporthook(blocknum, blocksize, totalsize):
    """Print simple download progress information during URL retrieval."""
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


def _download_url(url, targetname):
    """Download *url* to *targetname* using a proper User-Agent header."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        totalsize = int(response.headers.get("Content-Length", -1))
        blocksize = 8192
        blocknum = 0
        with open(targetname, "wb") as out:
            while True:
                buf = response.read(blocksize)
                if not buf:
                    break
                out.write(buf)
                blocknum += 1
                reporthook(blocknum, blocksize, totalsize)
    return targetname

def download(path,args):
    """Download a file to a target path and optionally decompress it in place."""
    url,targetname,*args=args
    targetname=os.path.join(path,targetname)
    decompress=None
    if len(args)>1:
        raise DownloaderError("Too many arguments")
    elif len(args)==1:
        decompress=args[0]
        if decompress not in ["zip","tar","gz","tgz","tar.gz","tar.bz2","tar.xz","7z"]:
            raise DownloaderError("Unknown decompression type")
        if decompress in ["gz"]: # compression without filenames
            targetname+="."+decompress
    try:
        fname=_download_url(url,targetname)
    except urllib.error.URLError as ex:
        reason = ex.reason if hasattr(ex, 'reason') else str(ex)
        print("Error downloading "+str(targetname)+": "+str(reason))
        raise DownloaderError("Can't download file")
    if decompress == "zip":
        ret=sp.call(["unzip",targetname,"-d",path],stdout=sys.stderr)
        if ret!=0:
            raise DownloaderError("Error extracting download")
    elif decompress == "tar" or decompress == "tar.gz":
        ret=sp.call(["tar","-xf",targetname,"-C",path],stdout=sys.stderr)
        if ret!=0:
            raise DownloaderError("Error extracting download")
    elif decompress == "tgz":
        ret=sp.call(["tar","-xfz",targetname,"-C",path],stdout=sys.stderr)
        if ret!=0:
            raise DownloaderError("Error extracting download")
    elif decompress == "tar.bz2":
        ret=sp.call(["tar","-xjf",targetname,"-C",path],stdout=sys.stderr)
        if ret!=0:
            raise DownloaderError("Error extracting download")
    elif decompress == "tar.xz":
        ret=sp.call(["tar","-xJf",targetname,"-C",path],stdout=sys.stderr)
        if ret!=0:
            raise DownloaderError("Error extracting download")
    elif decompress == "7z":
        ret=sp.call(["7z","x","-o" + path,"-y",targetname],stdout=sys.stderr)
        if ret!=0:
            raise DownloaderError("Error extracting download")
    elif decompress == "gz":
        ret=sp.call(["gunzip",targetname],stdout=sys.stderr)
        if ret!=0:
            raise DownloaderError("Error extracting download")

def _true(*arg):
    """Return true for every cached download record."""
    return True
    
def getfilter(active=None,url=None,compression=None,sort=None):
    """Build a filter and sort function for URL-backed download records."""
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
            filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive and url(largs[0])
        else:
            filterfn=lambda lmodule,largs,llocation,ldate,lactive: active == lactive
    elif url!=None:    
        filterfn=lambda lmodule,largs,llocation,ldate,lactive: url(largs[0])
    if sort == "date":
        sortfn=lambda lmodule,largs,llocation,ldate,lactive: date
    else:
        raise DownloaderError("Unknown sort key")
    return filterfn,sortfn
 
