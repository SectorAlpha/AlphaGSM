import os
import urllib.request
import json
import subprocess as sp
from server import ServerError
import re
import screen
from utils.httpparse import Page
from .vanilla import *
import gamemodules.minecraft.vanilla as van

# path to the download page
path_url = "www.technicpack.net/modpack/tekkitmain.552547"

def get_file_url():
  try:
     root_url, directory = path_url.split("/",1)
  except:
     raise Exception(path_url + " is not a valid download URL, needs a URL and a directory")
  print(root_url,directory)
  page = Page(root_url, directory)
  html = page.get_as_string()
  print(html)

  # parse the html to find possible download links
  file_url = None
  links = re.findall(r'<a(.*?)>',str(html)) # find a tags

  for a in links:
    link = a.split("=")[1].split(" ")[0]
    urllink = re.sub(r'^"|"$', '', link)
    if "Tekkit_Server_" in urllink:
      file_url = urllink

  return file_url

def configure(server,ask,*,port=None,dir=None,eula=None,version=None,url=None,check_versions=False,exe_name="Tekkit.jar",download_name="Tekkit.zip"):
  if url == None:
    # attempt to find the download url
    url = get_file_url()
  if url == None:
    raise Exception("invalid URL")
  return van.configure(server,ask,port=port,dir=dir,eula=eula,version=version,url=url,check_versions=check_versions,exe_name=exe_name,download_name=download_name)

def get_start_command(server):
  return ["java","-Xmx3G","-Xms2G","-jar",server.data["exe_name"],"nogui"],server.data["dir"]
