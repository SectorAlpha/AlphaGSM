import os
import re
import os.path
from os.path import isdir,islink,lexists as exists,join as joinpath
import shutil
import filecmp
from shutil import copy as copyfile

__all__=["update"]

SUFFIX=".~"
LOCALSUFFIX=SUFFIX+"local"
NEWSUFFIX=SUFFIX+"new"
OLDSUFFIX=SUFFIX+"old"

def update(old,new,target,linkdir=(),copy=(),skip=()):
  """ Update a folder tree taking into account the current tree, the original source tree and a new target tree.
      
      Any files or folders that match a regular expression in skip will be treated as if they don't exist in either old or new.
      Any folders that match a regular expression in linkdir will be linked rather than recursed into.
      Any folders that match a regular expression in copy will have them and all their contents copied recursively.
      Any files that match a regular expression in copy will be copied.
      All folders are matched with a trailing "/" and all paths are paths relative to the top of tree starting with a "."
      e.g. ./folder/file or ./folder/subfolder/ NOTE: suffix for folders is "/" even on windows
      
      The rules for the update are:
          Any files or folders that aren't from old and don't have version in new are left alone.
          
          Any files that have a current version thats same as in old but isn't wanted in new is removed.
          Any files that have a current version thats different to old but isn't wanted in new is renamed.
          
          Any files that are unchanged from old are updated to their equivelent in new.
          Any files that are unchanged between old and new are left as they are.
          Any files that are changed from old and want to be updated have the old and new copied next to it.
          
          symlinks in the current version are treated as unchanged files (even if they link to a directory)
          
          there are extra rules for edge cases mainly triggered if the rules or settings are changed
      
      This function returns True of everything was successfully updated and False otherwise
      """
  linkdir=[re.compile(pat) for pat in linkdir]
  copy=[re.compile(pat) for pat in copy]
  skip=[re.compile(pat) for pat in skip]
  if doupdate(old,new,target,".",linkdir,copy,skip,False):
    print("WARNING: Some files couldn't be updated. Once fixed please remove '{0}', '{1}' and '{2}' files and folders".format(LOCALSUFFIX,OLDSUFFIX,NEWSUFFIX))
    return False
  else:
    return True

def matchespatterns(path,patterns):
  """ Check if a path matches any of a list of patterns """
  return any(pat.match(path) is not None for pat in patterns)

def israwdir(path):
  """ Check if the path is directly a directory (i.e. don't follow symlinks) """
  return (not islink(path)) and isdir(path)

def ensureabsent(path):
  """ If path exists remove it whether it's a file or a folder """
  if exists(path):
    if israwdir(path):
      shutil.rmtree(path)
    else:
      os.remove(path)

def checkfiles(target,old):
  """ Check if two paths are both files with the same contents """
  return filecmp.cmp(target,old,shallow=False)

def checkandcleartrees(rel,target,old,skip):
  """ Clear out the target folder if it exists in old but isn't wanted in new.
      
      If directory recurse and if empty remove.
      If files are found that are not from old then leave them (and any ancestors) alone,
      If files are found that are changed then append ".~local" and again leave ancestors alone
      Otherwise we have unchanged files from old so remove them.
      This function returns True of the directory "target" was emptied and can be removed successfully
      """
  anyleft = False
  checklater=[]
  skiplater=[]
  for entry in os.listdir(target):
    if (entry[-len(OLDSUFFIX):]==OLDSUFFIX or entry[-len(NEWSUFFIX):]==NEWSUFFIX or 
        entry[-len(LOCALSUFFIX):]==LOCALSUFFIX):
      checklater.append(entry)
      continue
    targetentry=joinpath(target,entry)
    oldentry=joinpath(old,entry)
    relentry=joinpath(rel,entry)
    if israwdir(targetentry):
      if exists(oldentry) and not matchespatterns(relentry+"/",skip):
        #target is directory and old exists
        if not isdir(old):
          # target is dir but old isn't
          ensureabsent(targetentry+LOCALSUFFIX)
          os.rename(targetentry,targetentry+LOCALSUFFIX)
          skiplater.append(targetentry+LOCALSUFFIX)
          print("WARNING: file from old version is folder in local but isn't wanted in new.\nRenamed to '{0}".format(targetentry+LOCALSUFFIX))
        elif checkandcleartrees(relenetry,targetentry,oldentry,skip):
          # target and old both dirs and target now empty
          os.rmdir(targetentry)
        else:
          # target and old both dirs but couldn't empty target
          anyleft=True
      else:
        # in target but not in old so leave
        anyleft=True
    elif exists(oldentry) and not matchespatterns(relentry,skip):
      if checkfiles(targetentry,oldentry):
        # both exist and are files and match
        os.remove(targetentry)
      else:
        # both exist but are different
        ensusreabsent(targetentry+LOCALSUFFIX)
        os.rename(targetentry,targetentry+LOCALSUFFIX)
        skiplater.append(targetentry+LOCALSUFFIX)
        anyleft=True
        print("WARNING: file from old version has local changes but isn't wanted in new.\nRenamed to '{0}".format(targetentry+LOCALSUFFIX))
    else: #target is a file and no old so leave
      anyleft=True

  # process the old/new/local files from previous runs that haven't been updated/replaced this update
  for entry in checklater:
    if entry in skiplater:
      continue 
    targetentry=joinpath(target,entry)
    if isdir(targetentry):
      shutil.rmtree(targetentry)
    else:
      os.remove(targetentry)
  return not anyleft
        
def removeuneeded(old,target,rel,entry,skip):
  """ Remove an entry that isn't needed by new if it's from old 
      
      If there where any issues this returns True otherwise it returns False.
      """
  oldentry=joinpath(old,entry)
  targetentry=joinpath(target,entry)
  relentry=joinpath(rel,entry)
  matchentry=relentry
  if israwdir(targetentry):
    matchentry+="/"
  # only remove if was from old entries. Leave anything else behind (assume it was created by the game)
  # things in skip are treated as if not in old or new even if they actually are
  if exists(oldentry) and not matchespatterns(matchentry,skip):
    # old and target but no new so remove or if changed append .~local, 
    if israwdir(targetentry):
      if isdir(old):
        # target and old dirs but no new so need to recurse
        if checkandcleartrees(relentry,targetentry,oldentry,skip):
          # target and old both dirs and target now empty
          os.rmdir(targetentry)
        else:
          print("WARNING: directory {0} from old isn't wanted in new but some files weren't removed".format(targetentry))
          return True
      else:
        # target is dir but old isn't
        ensureabsent(targetentry+LOCALSUFFIX)
        os.rename(targetentry,targetentry+LOCALSUFFIX)
        print("WARNING: file from old version is folder in local but isn't wanted in new.\nRenamed to '{0}".format(targetentry+LOCALSUFFIX))
        return True
    elif islink(targetentry) or checkfiles(targetentry,oldentry):
      # link or unchanged file
      os.remove(targetentry)
    else:
      # not dir and not link and changed so rename
      ensureabsent(targetentry+LOCALSUFFIX)
      os.rename(targetentry,targetentry+LOCALSUFFIX)
      print("WARNING: File from old version has been changed in local but isn't wanted in new.\nRenamed to '{0}".format(targetentry+LOCALSUFFIX))
      return True
  return False

def updatefromnew(old,new,target,rel,entry,linkdir,copy,skip,forcecopy):
  """ Update the target entry from the new entry
      
      If there where any issues this returns True otherwise it returns False.
      """
  relentry=joinpath(rel,entry)
  newentry=joinpath(new,entry)
  targetentry=joinpath(target,entry)
  oldentry=joinpath(old,entry)
  matchentry=relentry
  if israwdir(newentry):
    matchentry+="/"
  if matchespatterns(matchentry,skip):
    return False
  # if dir and ( forcecopy or not linkdir ) then recurse possibly with forcecopy set
  # if not dir and forcecopy or copy then copy file
  # if ( not dir and not forcecopy and not copy ) or ( dir and linkdir and not forcecopy) then symlink file/dir
  if isdir(newentry) and (forcecopy or not matchespatterns(matchentry,linkdir)):
    # update recursively
    if forcecopy or matchespatterns(matchentry,copy):
      return doupdate(oldentry,newentry,targetentry,relentry,linkdir,copy,skip,True)
    else:
      return doupdate(oldentry,newentry,targetentry,relentry,linkdir,copy,skip,False)
  elif (not isdir(newentry)) and (forcecopy or matchespatterns(matchentry,copy)):
    # not dir and forcecopy or copy so copy files
    if exists(targetentry):
      if exists(oldentry) and checkfiles(targetentry,oldentry):
        # target, new and old and target=old so replace
        os.remove(targetentry)
        copyfile(newentry,targetentry)
      elif not exists(oldentry):
        # target, new and not old
        ensureabsent(targetentry+NEWSUFFIX)
        copyfile(newentry,targetentry+NEWSUFFIX)
        print("WARNING: File present in new version and local but not in old.\nLeaving your version ({0}) but putting new file in directory with it ({1}).\n".format(targetentry,targetentry+NEWSUFFIX))
        return True
      elif not checkfiles(newentry,oldentry):
        # target, new and old and old!=target and old!=new (target may or may not equal new)
        ensureabsent(targetentry+NEWSUFFIX)
        copyfile(newentry,targetentry+NEWSUFFIX)
        if not exists(targetentry+OLDSUFFIX): # if already an old file assume current is still based of that version not of the more recent old version
          copyfile(oldentry,targetentry+OLDSUFFIX)
        print("WARNING: File has update but local changes present.\nLeaving your version ({0}) but putting new and old files in directory with it\n({1} and {2})".format(targetentry,targetentry+NEWSUFFIX,targetentry+OLDSUFFIX))
        return True
      # else: pass # target, new and old but new=old so leave
    else:
      # not in target so just copy
      copyfile(newentry,targetentry)
  else:
    # symlink it
    if exists(targetentry):
      if islink(targetentry):
        os.remove(targetentry)
      else:
        ensureabsent(targetentry+LOCALSUFFIX)
        os.rename(targetentry,targetentry+LOCALSUFFIX)
        os.symlink(newentry,targetentry)
        print("WARNING: File exists locally but linking new version in.\nLocal version saved as {0}".format(targetentry+LOCALSUFFIX))
        return True
    else:
      os.symlink(newentry,targetentry)
  return False
  
def doupdate(old,new,target,rel,linkdir,copy,skip,forcecopy):
  """ Update a target folder from a new version
      
      If there where anu issues this returns True otherwise return False
      """
  anyfailed=False 
 
  # make sure we have a folder
  if islink(target):
    os.remove(target)
  if not isdir(target):
    os.mkdir(target)

  newentries=os.listdir(new)
  targetentries=os.listdir(target)
  
  # remove things that shouldn't be there but are
  for entry in targetentries:
    if (entry[-len(OLDSUFFIX):]==OLDSUFFIX or entry[-len(NEWSUFFIX):]==".~new" or 
        entry[-len(LOCALSUFFIX):]==LOCALSUFFIX):
      continue
    if entry not in newentries:
      anyfailed|=removeuneeded(old,target,rel,entry,skip)
  
  for entry in newentries:
    anyfailed|=updatefromnew(old,new,target,rel,entrym,linkdircopy,skip,forcecopy)
  return anyfailed
