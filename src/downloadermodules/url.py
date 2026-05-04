"""HTTP and archive-based download helpers used by the shared downloader cache."""

from downloader import DownloaderError
from datetime import date
import urllib.error
import urllib.request
import os.path
import shutil
import subprocess as sp
import sys
import time

URL_RETRIES = 3
URL_RETRY_DELAY_SECONDS = 5
URL_TIMEOUT_SECONDS = 60

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


def _download_url_with_curl(url, targetname, timeout, resume=False, retries=URL_RETRIES):
    """Download *url* to *targetname* with curl when urllib stalls."""

    curl_path = shutil.which("curl")
    if curl_path is None:
        raise FileNotFoundError("curl is not available")
    command = [
        curl_path,
        "--fail",
        "--location",
        "--http1.1",
        "--silent",
        "--show-error",
        "--retry",
        str(retries),
        "--retry-delay",
        str(URL_RETRY_DELAY_SECONDS),
        "--retry-all-errors",
        "--user-agent",
        USER_AGENT,
        "--connect-timeout",
        str(min(30, timeout)),
        "--speed-time",
        str(timeout),
        "--speed-limit",
        "1",
    ]
    if resume and os.path.exists(targetname) and os.path.getsize(targetname) > 0:
        command.extend(["--continue-at", "-"])
    command.extend([
        "--output",
        targetname,
        url,
    ])
    ret = sp.run(
        command,
        check=False,
        stdout=sp.DEVNULL,
        stderr=sp.PIPE,
        text=True,
    )
    if ret.returncode != 0:
        stderr = (ret.stderr or "").strip()
        raise OSError(stderr or "curl download failed")
    return targetname


def _download_url(url, targetname, timeout=URL_TIMEOUT_SECONDS):
    """Download *url* to *targetname* using a proper User-Agent header."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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
    except (OSError, urllib.error.URLError) as exc:
        try:
            return _download_url_with_curl(url, targetname, timeout)
        except (FileNotFoundError, OSError):
            raise exc


def _parse_timeout_seconds(value):
    """Parse a positive per-download timeout value."""

    try:
        timeout = int(value)
    except (TypeError, ValueError) as exc:
        raise DownloaderError("Invalid download timeout") from exc
    if timeout <= 0:
        raise DownloaderError("Invalid download timeout")
    return timeout


def _parse_transport(value):
    """Parse an optional transport hint for direct URL downloads."""

    transport = str(value).strip().lower()
    if transport not in ("auto", "curl"):
        raise DownloaderError("Invalid download transport")
    return transport

def download(path,args):
    """Download a file to a target path and optionally decompress it in place."""
    url,targetname,*args=args
    targetname=os.path.join(path,targetname)
    decompress=None
    timeout = URL_TIMEOUT_SECONDS
    transport = "auto"
    if len(args)>3:
        raise DownloaderError("Too many arguments")
    elif len(args)>=1:
        decompress=args[0]
        if decompress not in ["zip","tar","gz","tgz","tar.gz","tar.bz2","tar.xz","7z"]:
            raise DownloaderError("Unknown decompression type")
        if decompress in ["gz"]: # compression without filenames
            targetname+="."+decompress
        if len(args)>=2:
            timeout = _parse_timeout_seconds(args[1])
        if len(args)==3:
            transport = _parse_transport(args[2])
    part_targetname = targetname + ".part"
    for attempt in range(URL_RETRIES):
        try:
            if transport == "curl":
                resume = False
                if os.path.exists(part_targetname):
                    os.remove(part_targetname)
            else:
                resume = False
                try:
                    os.remove(part_targetname)
                except FileNotFoundError:
                    pass
            if transport == "curl":
                _download_url_with_curl(
                    url,
                    part_targetname,
                    timeout=timeout,
                    resume=resume,
                    retries=0,
                )
            else:
                _download_url(url, part_targetname, timeout=timeout)
            os.replace(part_targetname, targetname)
            break
        except (OSError, urllib.error.URLError) as ex:
            reason = ex.reason if hasattr(ex, 'reason') else str(ex)
            print("Error downloading " + str(targetname) + ": " + str(reason))
            if transport == "curl":
                try:
                    os.remove(part_targetname)
                except FileNotFoundError:
                    pass
            else:
                try:
                    os.remove(part_targetname)
                except FileNotFoundError:
                    pass
            if attempt + 1 < URL_RETRIES:
                print("Retrying in %d seconds..." % (URL_RETRY_DELAY_SECONDS,))
                time.sleep(URL_RETRY_DELAY_SECONDS)
            else:
                raise DownloaderError("Can't download file") from ex
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
 
