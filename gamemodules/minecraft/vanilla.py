import os
import urllib.request
import json
import time
import datetime
import subprocess as sp
from server import ServerError
import re
import screen
import downloader
import utils.updatefs
from .custom import *
from . import custom as cust
from utils.cmdparse.cmdspec import CmdSpec,OptSpec,ArgSpec


command_args=command_args.copy()
command_args["setup"]=command_args["setup"].combine(CmdSpec(options=(OptSpec("v",["version"],"Version of minecraft to download. Overriden by the url option","version","VERSION",str),
                                                OptSpec("u",["url"],"Url to download minecraft from. See https://minecraft.net/download for latest download.","url","URL",str))))

def configure(server,ask,port=None,dir=None,*,eula=None,version=None,url=None,exe_name="minecraft_server.jar",download_name="minecraft_server.jar",download_data=None):
    allversions=[]
    latest=None
    if version is not None or url is None:
        try:
            versionsfile=urllib.request.urlopen("https://s3.amazonaws.com/Minecraft.Download/versions/versions.json")
            versions=json.loads(versionsfile.read().decode("utf-8"))
            latest=versions["latest"]["release"]
            allversions=[v["id"] for v in versions["versions"] if v["type"] in ["release","snapshot"]] #ditch other types as don't have servers
        except Exception as ex:
            print("Error downloading list of versions: "+str(ex)+"\nlisting versions and latest version will fail")

        if len(allversions)>0 and version is None:
            if "version" in server.data:
                version=server.data["version"]
            else:
                version="latest"
            if ask:
                while True:
                    inp=input("Please specify the version of minecraft to use.\nEnter \"latest\" for the latest version ("+str(latest)+
                                        "), \"None\" for a custom download url or \"list\" to get a list of versions\n: ["+str(version)+"] ").strip()
                    if inp.lower() == "list":
                        print("'"+"', '".join(allversions)+"'")
                        continue
                    elif inp.lower()=="none":
                        version=None
                    elif inp.lower()=="latest":
                        version=latest
                    elif inp!="":
                        version=inp
                    if version is not None and version not in allversions:
                        if input(version+" is not in the list of versions. Use anyway? (y/yes or n/no): ").strip().lower() not in ("y","yes"):
                            continue
                    break
            if version=="latest":
                version=latest
    server.data["version"]=version

    if version is not None:
        url="https://s3.amazonaws.com/Minecraft.Download/versions/"+version+"/minecraft_server."+version+".jar"

    if url is None:
        if "url" in server.data and server.data["url"] is not None:
            url=server.data["url"]
        else:
            url="https://s3.amazonaws.com/Minecraft.Download/versions/1.8.3/minecraft_server.1.8.3.jar"
        if ask:
            inp=input("Please give the download url for the minecraft server:\n["+url+"]\n ").strip()
            if inp!="":
                url=inp
    server.data["url"]=url
    
    server.data["download_name"] = download_name
    if download_data is not None:
        server.data["download"]=download_data

    return cust.configure(server,ask,port,dir,eula=eula,exe_name=exe_name)

def install(server,*,eula=False):
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    mcjar=os.path.join(server.data["dir"],server.data["exe_name"])
    mcdwl=os.path.join(server.data["dir"],server.data["download_name"])

    # if URL has changed, or the executable does not exist, redownload the server
    if "current_url" not in server.data or server.data["current_url"]!=server.data["url"] or not os.path.isfile(mcjar):
        download_name, download_extension = os.path.splitext(server.data["download_name"])
        print(download_extension)
        decompress=()
        if download_extension == ".zip":
            decompress=("zip",)
        try:
            downloadpath=downloader.getpath("url",(server.data["url"],server.data["download_name"])+decompress)
            if decompress==():
                try:
                    os.remove(mcjar)
                except FileNotFoundError:
                    pass
                os.symlink(os.path.join(downloadpath,server.data["exe_name"]),mcjar)
            else:
                basetagpath=os.path.join(server.data["dir"],".~basetag")
                try:
                    oldpath=os.readlink(basetagpath)
                except FileNotFoundError:
                    oldpath="/dev/null/INVALID"
                else:
                    os.remove(basetagpath)
                utils.updatefs.update(oldpath,downloadpath,server.data["dir"],server.data["download"]["linkdir"],server.data["download"]["copy"])
                os.symlink(downloadpath,basetagpath)
        except downloader.DownloaderError as ex:
            print("Error downloading minecraft_server.jar: ")
            raise ServerError("Error setting up server. Server file isn't already downloaded and can't download requested version")
        server.data["current_url"]=server.data["url"]
    else:
        print("Skipping download")
    server.data.save()

    cust.install(server,eula=eula)
