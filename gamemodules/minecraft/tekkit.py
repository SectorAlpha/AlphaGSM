import os
import urllib.request
import json
import subprocess as sp
from server import ServerError
import re
import screen
from core.httpparse import Page
from .vanilla import *
import gamemodules.minecraft.vanilla as van

# path to the download page
path_url = "www.technicpack.net/modpack/tekkitmain.552547"

def get_file_url():
  root_url, directory = path_url.split("/",1)
  page = Page(root_url, directory)
  html = page.get_as_string()

  # parse the html to find possible download links
  file_url = None
  paragraphs = re.findall(r'<a(.*?)>',str(html)) # find a tags

  for p in paragraphs:
    link = p.split("=")[1].split(" ")[0]
    urllink = re.sub(r'^"|"$', '', link)
    if "Tekkit_Server_" in urllink:
      file_url = urllink

  return file_url

def configure(server,ask,*,port=None,dir=None,eula=None,version=None,url=None,check_versions=False):
  if url == None:
    # attempt to find the download url
    url = get_file_url()
  if url == None:
    raise Exception("invalid URL")
  print(url)
  return van.configure(server,ask,port=port,dir=dir,eula=eula,version=version,url=url,check_versions=check_versions)

def install(server,*,eula=False,exe_name="Tekkit.jar",download_name="Tekkit.zip"):
  print("lol try this")
  return van.install(server,eula=eula,exe_name=exe_name,download_name=download_name)

def get_start_command(server):
  return ["java","-Xmx3G","-Xms2G","-jar",server.data["exe_name"],"nogui"],server.data["dir"]
