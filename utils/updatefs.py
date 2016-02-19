import os
import re
from os.path import isdir,islink,exists,join as joinpath


def update(old,new,target,linkdir=(),copy=()):
  linkdir=[re.compile(pat) for pat in server.data['linkdir']]
  copy=[re.compile(pat) for pat in server.data['copy']]
  _doupdate(old,new,target,".",linkdir,copy,False)

def israwdir(path):
  return (not islink(path)) and isdir(path)

def checkandcleartrees(target,old):
  #TODO: Implement! 

def checkfiles(target,old):
  return filecmp.cmp(target,old,shallow=False)

def _doupdate(old,new,target,rel,linkdir,copy,forcecopy):
  # do we need to force copying? (no point checking if already forced)
  if (not focecopy) and any(pat.match(rel+"/") is not None for pat in copy):
    forcecopy=True

  # make sure we have a folder
  if islink(destpath):
    os.remove(destpath)
  if not isdir(destpath):
    os.path.mkdir(destpath)

  newentries=os.listdir(new)
  targetentries=os.listdir(target)
  
  # remove things that shouldn't be there but are
  for entry in targetentries:
    if entry[-5:]==".~old" or entry[-5:]==".~new" or entry[-5:]==".local":
      continue
    if entry not in newnetries:
      oldentry=joinpath(old,entry)
      #only remove if was from old entries. Leave anything else behind (assume it was created by the game)
      if exists(oldentry):
        # old and target but no new so remove or if changed append .old, 
        targetentry=joinpath(target,entry)
        if israwdir(targetentry):
          checkanddcleartree(targetentry,oldentry)
        elif islink(targetentry) or checkfiles(targetentry,oldentry):
          os.remove(targetentry)
        else:
          if exists(targetentry+".~local")
            os.remove(targeentry+".~local")
          os.rename(targetentry,targetentry+".~local")
          print("WARNING: File from old version has been changed in local but isn't wanted in new. \n Renamed to '{0}".format(targetentry+".~local"))
  
  for entry in newentries:
    # add new entries
    relentry=joinpath(rel,entry)
    newentry=joinpath(old,entry)
    targetentry=joinpath(target,entry)
    oldentry=joinpath(old,entry)
    # if dir and ( forcecopy or not linkdir ) then recurse possibly with forcecopy set
    # if not dir and forcecopy or copy then copy file
    # if ( not dir and not forcecopy and not copy ) or ( dir and linkdir and not forcecopy) then symlink file/dir
    if isdir(newentry) and (forcecopy or not any(pat.match(relentry+"/") is not None for pat in linkdir)):
      # update recursively
      if (not forcecopy) and any(patmatch(relentry+"/") is not None for pat in copy):
        forcecopy=True
      _doupdate(oldentry,newentry,targetentry,relentry,linkdir,copy,forcecopy
    elif (not isdir(newentry)) and (forcecopy or any(pat.match(relentry) is not None for pat in copy)):
      # copy files
      if exists(targetentry):
        if exists(oldentry) and checkfiles(targetentry,oldentry):
          # target, new and old and target=old so replace
          os.remove(targetentry)
          copyfile(newentry,targetentry)
        elif not exists(oldentry)
          # don't delete a changed file
          # copy new and old into directory and leave current
          if exists(targetentry+".~new"):
            os.remove(targetentry+".~new")
          copyfile(newentry,targetentry+".~new")
          print("WARNING: File present in new version and local but not in old.\nLeaving your version ({0}) but putting new file in directory with it ({1}).\n".format(targetentry,targetentry+".~new")
        # don't need to do anything if file hasn't changed between versions
        elif not checkfiles(newentry,oldentry):
          if exists(targetentry+".~new"):
            os.remove(targetentry+".~new")
          copyfile(newentry,targetentry+".~new")
          if exists(targetentry+".~old"):
            copyfile(oldentry,targetentry+".~old")
          print("WARNING: File has update but local changes present.\n Leaving your version ({0}) but putting new and old files in directory with it\n({1} and {2})".format(targetentry,targetentry+".~new",targetentry+".~old")
      else:
        copyfile(newentry,targetentry)
    else:
      # symlink it
      if exists(targetentry):
        if islink(targetentry):
          os.remove(targetentry)
        else:
          os.rename(targetentry,targetentry+".~local")
          print("WARNING: File exists locally but linking new version in. Local version saved as {0}".format(targetentry+".~local"))
      os.symlink(newentry,targetentry)
