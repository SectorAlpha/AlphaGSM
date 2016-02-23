import os
import urllib.request
import json
import subprocess as sp
from server import ServerError
import re
import screen
import urllib.request
from .vanilla import *
import gamemodules.minecraft.vanilla as van

# path to the download page
MODPACK_URL = "http://www.technicpack.net/modpack/tekkitmain.552547"

def get_file_url(modpack_url):
  try:
    response = urllib.request.urlopen(modpack_url)
  except:
    raise ServerError("Invalid URL")
  html = response.read()
  
  # parse the html to find possible download links
  file_url = None
  links = re.findall(r'<a(.*?)>',str(html)) # find a tags

  for a in links:
    link = a.split("=")[1].split(" ")[0]
    urllink = re.sub(r'^"|"$', '', link)
    if "Tekkit_Server_" in urllink:
      file_url = urllink

  return file_url

command_args=command_args.copy()
command_args["setup"]=([],[("PORT","The port for the server to listen on",int),("DIR","The Directory to install minecraft in",str)],False,
                       [("u",["url"],"Url to download tekkit from. See http://www.technicpack.net/modpack/tekkitmain.552547 for latest download.","url","URL",str),
                        ("p",["modpack"],"Url for the modpack page. Used to locate the latest server url.","modpack_url","URL",str)])

def configure(server,ask,*,port=None,dir=None,url=None,modpack_url=None,exe_name="Tekkit.jar",download_name="Tekkit.zip"):
  if url == None:
    if "url" in server.data and server.data["url"] is not None:
      url=server.data["url"]
    # attempt to find the download url
  if ask or url is None:
    if modpack_url == None:
      if "modpack_url" in server.data and server.data["modpack_url"] is not None:
        modpack_url=server.data["modpack_url"]
    if modpack_url is None:
      modpack_url = MODPACK_URL
    server.data["modpack_url"]=modpack_url
    latest_url = get_file_url(modpack_url)
    if url is None:
      url = latest_url
    if ask:
      print("Which url should we use to download tekkit?\nThe latest url is '{}'.".format(latest_url))
      inp=input("Please enter the url to download tekkit from or 'latest' for the latest version: ["+url+"] ").strip()
      if inp!="":
        if inp.lower() == "latest":
          url=latest_url
        else:
          url=inp     
  if url == None:
    raise ServerError("No download URL available")
  return van.configure(server,ask,port=port,dir=dir,eula=False,version=None,url=url,exe_name=exe_name,download_name=download_name,download_data={"linkdir":(r"\./mods/",r"\./libraries/"),"copy":(r"\./config/",r"\./server.properties")})

def get_start_command(server):
  return ["java","-Xmx3G","-Xms2G","-jar",server.data["exe_name"],"nogui"],server.data["dir"]
