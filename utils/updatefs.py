import os
import re
import os.path
from os.path import isdir,islink,lexists as exists,join as joinpath
import shutil
import filecmp
from shutil import copy as copyfile

def update(old,new,target,linkdir=(),copy=()):
  """ Update a folder tree taking into account the current tree, the originalsource tree and a new target tree.
         
      Any folders that match a regular expression in linkdir will be linked rather than recursed into.
      Any folders that match a regular expression in copy will have them and all their contents copied recursively.
      Any files that match a regular expression in copy will be copied.
      All folders are matched with a trailing "/".
   
      The rules forthe update are:
          Any files or folders that aren't from source and don't have version in new are left alone.
          
          Any files that have a current version thats same as in old but isn't wanted in new is removed.
          Any files that have a current version thats different to old but isn't wanted in new is renamed.
          
          Any files that are unchanged from old are updated to their equivelent in new.
          Any files that are unchanged between old and new are left as they are.
          Any files that are changed from old and want to be updated have the old and new copied next to it.

          symlinks in the current version are treated as unchanged files (even if they link to a directory)
          
          there are extra rules for edge cases mainly triggered if the rules or settings are changed

      """
  print(linkdir)
  print(copy)
  linkdir=[re.compile(pat) for pat in linkdir]
  copy=[re.compile(pat) for pat in copy]
  return _doupdate(old,new,target,".",linkdir,copy,False)

def israwdir(path):
  return (not islink(path)) and isdir(path)

def checkandcleartrees(target,old):
  """Function to clear out the target if the old exists but new doesn't.
     If directory recurse and if empty remove.
     If files are found that are not from old then leave them and any ancestors alone,
     If files are found that are changed then append ".~local" and again leave ancestors along
     Otherwise we have unchanged files from old so remove them.
     This function returns True of the directory "target" was emptied and removed successfully"""
  anyleft = False
  checklater=[]
  skiplater=[]
  for entry in os.listdir(target):
    if entry[-5:]==".~old" or entry[-5:]==".~new" or entry[-7:]==".~local":
      checklater.append(entry)
      continue
    targetentry=joinpath(target,entry)
    oldentry=joinpath(old,entry)
    if israwdir(targetentry):
      if exists(oldentry):
        if not isdir(old):
          # target is dir but old isn't
          if exists(targetentry+".~local"):
            if isdir(targetentry+".~local"):
              shutil.rmtree(targetentry+".~local")
            else:
              os.remove(targetentry+".~local")
          os.rename(targetentry,targetentry+".~local")
          skiplater.append(targetentry+".~local")
          print("WARNING: file from old version is folder in local but isn't wanted in new. \n Renamed to '{0}".format(targetentry+".~local"))
        elif checkandcleartrees(targetentry,oldentry):
          # target and old both dirs and target now empty
          os.rmdir(targetentry)
        else:
          # target and old both dirs but couldn't empty target
          anyleft=True
      else:
        # in target but not in old so leave
        anyleft=True
    elif exists(oldentry):
      if checkfiles(targetentry,oldentry):
        # both exist and are file and match
        os.remove(targetentry)
      else:
        # both exist but are different
        if exists(targetentry+".~local"):
          if isdir(targetentry+".~local"):
            shutil.rmtree(targetentry+".~local")
          else:
            os.remove(targetentry+".~local")
        os.rename(targetentry,targetentry+".~local")
        skiplater.append(targetentry+".~local")
        print("WARNING: file from old version has local changes but isn't wanted in new. \n Renamed to '{0}".format(targetentry+".~local"))
    # else target is a file and no old so leave

  # process the backup files from previous runs that haven't been updated/replaced this update
  for entry in checklater:
    if entry in skiplater:
      continue 
    targetentry=joinpath(target,entry)
    if isdir(targetentry):
      shutil.rmtree(targetentry)
    else:
      os.remove(targetentry)
  return not anyleft
        
def checkfiles(target,old):
  return filecmp.cmp(target,old,shallow=False)

def _doupdate(old,new,target,rel,linkdir,copy,forcecopy):
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
    if entry[-5:]==".~old" or entry[-5:]==".~new" or entry[-7:]==".~local":
      continue
    if entry not in newentries:
      oldentry=joinpath(old,entry)
      #only remove if was from old entries. Leave anything else behind (assume it was created by the game)
      if exists(oldentry):
        # old and target but no new so remove or if changed append .~local, 
        targetentry=joinpath(target,entry)
        if israwdir(targetentry):
          if isdir(old):
            # target and old dirs but no new so need to recurse
            if checkandcleartrees(targetentry,oldentry):
              # target and old both dirs and target now empty
              os.rmdir(targetentry)
            else:
              anyfailed=True
              print("WARNING: directory {0} from old isn't wanted in new but some files weren't removed".format(targetentry))
          else:
            # target is dir but old isn't
            if exists(targetentry+".~local"):
              if isdir(targetentry+".~local"):
                shutil.rmtree(targetentry+".~local")
              else:
                os.remove(targetentry+".~local")
            os.rename(targetentry,targetentry+"~.local")
            anyfailed=True
            print("WARNING: file from old version is folder in local but isn't wanted in new. \n Renamed to '{0}".format(targetentry+".~local"))
        elif islink(targetentry) or checkfiles(targetentry,oldentry):
          # link or unchanged file
          os.remove(targetentry)
        else:
          #not dir and not link and changed so rename
          if exists(targetentry+".~local"):
            if isdir(targetentry+".~local"):
              shutil.rmtree(targetentry+".~local")
            else:
              os.remove(targetentry+".~local")
          os.rename(targetentry,targetentry+".~local")
          anyfailed=True
          print("WARNING: File from old version has been changed in local but isn't wanted in new. \n Renamed to '{0}".format(targetentry+".~local"))
  
  for entry in newentries:
    # add new entries
    relentry=joinpath(rel,entry)
    newentry=joinpath(new,entry)
    targetentry=joinpath(target,entry)
    oldentry=joinpath(old,entry)
    # if dir and ( forcecopy or not linkdir ) then recurse possibly with forcecopy set
    # if not dir and forcecopy or copy then copy file
    # if ( not dir and not forcecopy and not copy ) or ( dir and linkdir and not forcecopy) then symlink file/dir
    if isdir(newentry) and (forcecopy or not any(pat.match(relentry+"/") is not None for pat in linkdir)):
      # update recursively
      if forcecopy or any(pat.match(relentry+"/") is not None for pat in copy):
        anyfailed|=_doupdate(oldentry,newentry,targetentry,relentry,linkdir,copy,True)
      else:
        anyfailed|=_doupdate(oldentry,newentry,targetentry,relentry,linkdir,copy,False)
    elif (not isdir(newentry)) and (forcecopy or any(pat.match(relentry) is not None for pat in copy)):
      # not dir and forcecopy or copy so copy files
      if exists(targetentry):
        if exists(oldentry) and checkfiles(targetentry,oldentry):
          # target, new and old and target=old so replace
          os.remove(targetentry)
          copyfile(newentry,targetentry)
        elif not exists(oldentry):
          # don't delete a changed file
          # copy new and old into directory and leave current
          if exists(targetentry+".~new"):
            os.remove(targetentry+".~new")
          copyfile(newentry,targetentry+".~new")
          anyfailed=True
          print("WARNING: File present in new version and local but not in old.\nLeaving your version ({0}) but putting new file in directory with it ({1}).\n".format(targetentry,targetentry+".~new"))
        # don't need to do anything if file hasn't changed between versions
        elif not checkfiles(newentry,oldentry):
          if exists(targetentry+".~new"):
            os.remove(targetentry+".~new")
          copyfile(newentry,targetentry+".~new")
          if not exists(targetentry+".~old"):
            copyfile(oldentry,targetentry+".~old")
          anyfailed=True
          print("WARNING: File has update but local changes present.\n Leaving your version ({0}) but putting new and old files in directory with it\n({1} and {2})".format(targetentry,targetentry+".~new",targetentry+".~old"))
      else:
        copyfile(newentry,targetentry)
    else:
      # symlink it
      if exists(targetentry):
        if islink(targetentry):
          os.remove(targetentry)
        else:
          if exists(targetentry+".~local"):
            if isdir(targetentry+".~local"):
              shutil.rmtree(targetentry+".~local")
            else:
              os.remove(targetentry+".~local")
          os.rename(targetentry,targetentry+".~local")
          anyfailed=True
          print("WARNING: File exists locally but linking new version in. Local version saved as {0}".format(targetentry+".~local"))
      os.symlink(newentry,targetentry)
  return anyfailed
