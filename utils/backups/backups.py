""" Backup a folder based on profiles and a schedule

The config parameter to backup has the format:
{'profiles':
  {'name1':
    {'base':'othername',
     'targets':['list', 'of', 'targets', 'to', 'include', 'in', 'the', 'backup'],
     'exclusions':['list', 'of', 'patterns', 'that', 'match', 'files', 'and', 'folders', 'to', 'exclude'],
     'replace_targets': True/False,
     'replace_exclusions': True/False,
     'lifetime':(maximumage,ageunit)
    },
    ...
  },
  'schedule':[('profilename',timebetweenupdates,timeunit), ...]
}

Each profile describes a type of backup including what is included in the backup and how long it is kept for.
Either the 'base' entry or the 'targets' and 'exclusions' entries must be specified. If 'base' is specified
then this profiles inherits settings from the named profile. If the profile has a base and has some targets
specified then if 'replace_targets' is True the base profiles targets are replaced, otherwise the are combined.
The equivelent applies with exclusions and replace_exclusions. It is not valid to have a cycle in the 'base'
relations and if this occurs the result is unspecified.
NOTE: Profile names can only contain alphanumerics and _.

If a profile has a lifetime then any backups older than this amount of time are automatically deleted after
the update.

The schedule is an ordere list of entries. Each entry is tried in turn and if the latest backup of the
specified profile is older than the specified amount of time then that profile will be used. The last entry
should have a timeperiod of 0 so at least one entry will match.

It is also possible to call backup and manually specify a backup profile to use.

The timespecs are an amount and a unit where the unit is one of the strings 'year','month','week','day'.
Months and years are calender months and years respectively and month rounds the day down if out of
range for the resulting month.
"""
import subprocess as sp
import os
import datetime
import calendar
from utils.settings import settings

BACKUPDIR=settings.user.getsection('backup').get('directory',"backup")
TIMESTAMPFORMAT=settings.user.getsection('backup').get('timestamptformat',"%Y.%m.%d %H:%M:%S.%f")

__all__=["BackupError","backup","checkdatavalue"]

class BackupError(Exception):
  pass

def getprofiledata(config,profile):
  try:
    profiledata=config["profiles"][profile]
  except KeyError as ex:
    raise BackupError("Unknown backup profile '{}'".format(profile))
  if "base" in profiledata:
    newprofiledata=getprofiledata(config,profiledata["base"]).copy()
    if "targets" in profiledata:
      if "replace_targets" in profiledata and profiledata["replace_targets"] or "targets" not in newprofiledata:
        newprofiledata["targets"]=profiledata["targets"]
      else:
        newprofiledata["targets"]=newprofiledata["targets"]+profiledata["targets"]
    if "exclusions" in profiledata:
      if "replace_exclusions" in profiledata and profiledata["replace_exclusions"] or "exclusions" not in newprofiledata:
        newprofiledata["exclusions"]=profiledata["exclusions"]
      else:
        newprofiledata["exclusions"]=newprofiledata["exclusions"]+profiledata["exclusions"]
    if "lifetime" in profiledata:
      newprofiledata["lifetime"]=profiledata["lifetime"]
    return newprofiledata
  else:
    return profiledata

def applydelta(timestamp,amount,unit):
  if amount == 0:
    return timestamp
  if unit.lower() == "year":
    return timestamp.replace(year=timestamp.year+amount)
  if unit.lower() =="month":
   year,month=divmod(timestamp.month+amount-1,12)
   month+=1
   year+=timestamp.year
   day = min(timestamp.day,calendar.monthrange(year,month)[1])
   return timestamp.replace(year=year,month=month,day=day)
  if unit.lower() in ["week","day"]:
    return timestamp+datetime.timedelta(**{unit.lower()+"s":amount})
  print("ERROR: Unknown time unit. Treating as 0")
  return timestamp

def doschedule(config,now,backups):
  schedule=config["schedule"]
  for tag,maxage,ageunit in schedule:
    if tag not in backups or backups[tag][-1][1]<applydelta(now,-maxage,ageunit):
      return tag
  return tag

def backup(dir,config,profile=None):
  now=datetime.datetime.utcnow()
  if not os.path.exists(os.path.join(dir,BACKUPDIR)):
    os.mkdir(os.path.join(dir,BACKUPDIR))
  backups={}
  for f in os.listdir(os.path.join(dir,BACKUPDIR)):
    if f[-4:]!=".zip" or f[0]==".":
      continue
    tag,timestamp=f[:-4].split(" ",1)
    timestamp=datetime.datetime.strptime(timestamp,TIMESTAMPFORMAT)
    if tag not in backups:
      backups[tag]=[]
    backups[tag].append((f,timestamp))
  for key,val in backups.items():
    val.sort(key=lambda ft: ft[1])
 

  if profile==None:
    profile=doschedule(config,now,backups)
  data=getprofiledata(config,profile)
  targetname=os.path.join(BACKUPDIR,profile+" "+now.strftime(TIMESTAMPFORMAT)+".zip")
  cmd=['zip','-ry',targetname]+data['targets']+["-x",os.path.join(BACKUPDIR,"*")]
  if 'exclusions' in data and len(data['exclusions'])>0:
    cmd+=data["exclusions"]
  try:
    sp.check_call(cmd,cwd=dir)
  except sp.CalledProcessError as ex:
    print("Error backing up the server")
    return
  
  for tag,files in backups.items():
    profile=getprofiledata(config,tag)
    if "lifetime" not in profile:
      continue
    maxage,ageunit=profile["lifetime"]
    earliesttimestamp=applydelta(now,-maxage,ageunit)
    for filename,timestamp in files:
      if timestamp<earliesttimestamp:
        print("Removing out of date backup: {}".format(filename))
        os.remove(os.path.join(os.path.join(dir,BACKUPDIR),filename))
      else:
        # sorted by date so can't have "newer" ones be older
        break

def checkdatavalue(data,key,*value):
  if key[0] == 'profiles':
    if not key[1].isidentifier():
      raise BackupError("Invalid backup profile name")
    if len(key) == 2:
      if value == ("DELETE",):
        return "DELETE"
    if len(key) != 3:
      raise BackupError("Must specify what profile and key within the profile to set")
    if key[2] in ("targets","exclusions"):
      if len(value) == 1 and value == ("DELETE",):
        return "DELETE"
      else:
        return list(value)
    elif key[2] in ("replace_targets","replace_exlclusions"):
      if len(value) != 1:
        raise BackupError("key only takes one value")
      if value[0].lower() in ("t","y","true","yes","on"):
        return True
      elif value[0].lower() in ("f","n","false","no","off"):
        return False
      else:
        raise BackupError("Invalid value for key. Only boolean values allowed")
    elif key[2] == "base":
      if len(value)!=1:
        raise BackupError("key only takes one value")
      if value == ("DELETE",):
        return "DELETE"
      if value[0] not in data["profiles"]:
        raise BackupError("Profile base must be a valid profile")
      return value[0]
    elif key[2] == "lifetime":
      if len(value) != 2:
        raise BackupError("lifetime must have two values")
      amount,unit=value
      try:
        amount=int(amount)
      except ValueError:
        raise BackupError("The first value must be an integer")
      if unit.lower() not in ("year","month","week","day"):
        raise BackupError("The second value must be a valid time unit: 'year', 'month', 'week' or 'day'")
      return [amount,unit]
    else:
      raise BackupError("Unknown key")
  elif key[0] == 'schedule':
    if len(key) != 2:
      raise BackupError("Must specify an entry in the schedule to set")
    if value == ("DELETE",):
      return "DELETE"
    if len(value) != 3:
      raise BackupError("A schedule entry must have three values")
    profile,amount,unit=value
    if profile not in data["profiles"]:
      raise BackupError("The first value must be a valid profile")
    try:
      amount=int(amount)
    except ValueError:
      raise BackupError("The second value must be an integer")
    if unit.lower() not in ("year","month","week","day"):
      raise BackupError("The third value must be a valid time unit: 'year', 'month', 'week' or 'day'")
    return [profile,amount,unit]
  else:
    raise BackupError("Invalid key")

