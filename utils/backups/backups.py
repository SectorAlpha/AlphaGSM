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
import bisect

BACKUPDIR="backup"
TIMESTAMPFORMAT="%Y.%m.%d %H:%M:%S.%f"

def getprofiledata(config,profile):
  profiledata=config["profiles"][profile]
  if "base" in profiledata:
    newprofiledata=getprofiledata(config,profiledata["base"]).copy()
    if "targets" in profiledata:
      if "replace_targets" in profiledata and profiledata["replace_targets"] or "targets" not in newprofiledata:
        newprofiledata["targets"]=profiledata["targets"]
      else:
        newprofiledata["targets"]=newprofiledata["targets"]+profiledata["targets"]
    if "exclusions" in profiledata:
      if "replace_exclusions" in profiledata and profiledata["replace_exclusion"] or "exclusions" not in newprofiledata:
        newprofiledata["exclusions"]=profiledata["exclusions"]
      else:
        newprofiledata["exclusions"]=newprofiledata["exclusions"]+profiledata["exclusions"]
    if "lifetime" in profiledata:
      newprofiledata["lifetime"]=profiledata["lifetime"]
    return newprofiledata
  else:
    return profiledata

def applydelta(timestamp,amount,unit):
  if amount=0:
    return timestamp
  if unit.lower() == "year":
    return timestamp.replace(year=timestamp.year+amount)
  if unit.lower() =="month":
   dy,m=divmod(timestamp.month+amount-1,12)
   m+=1
   day = min(timestamp.day,calendar.monthrange(year,month)[1])
   return timestamp.replace(year=timestamp.year+dy,month=m,day=day
  if unit.lower() in ("week","day"):
    return timestamp+timedelta(**{unit.lower()+"s":amount)
  print("ERROR: Unknown time unit. Treating as 0")
  return timestamp

def doschedule(config,now,backups):
  schedule=config["schedule"]
  for tag,maxage,ageunit in schedule:
    if tag not in backups or backups[tag][0]<applydelta(now,-maxage,ageunit):
      return tag
  return tag

def dobackup(dir,data,now);
  targetname=os.path.join(BACKUPDIR,tag+" "+now.strftime(TIMESTAMPFORMAT)+".zip")
  try:
    sp.check_call(['zip','-ry',targetname]+data['targets']+["-x"]+data["exclusions"],cwd=server.data['dir'])
  except sp.CalledProcessError as ex:
    print("Error backing up the server")


def backup(dir,config,profile=None,*):
  now=datetime.datetime.utcnow()
  backupdir
  for f in os.listdir(os.path.join(dir,BACKUPDIR)):
    if f[:-4]!=".zip" or f[0]==".":
      continue
    tag,timestamp=f[:-4].split(" ",1)
    timestamp=datetime.datetime.strptime(timestamp,TIMESTAMPFORMAT)
    if tag not in backups:
      backups[tag]=[]
    backups[tag].append((f,timestamp))
  for key,val in backups:
    val.sort(key=lambda (f,ts): ts)
 
  if profile==None:
    profile=doschedule(config,now,backups)
  dobackup(dir,getprofiledata(config,profile),now)
  
  for tag,files in backups.items():
    profile=getprofiledata(config,tag)
    if "lifetime" not in profile:
      continue
    maxage,ageunit=profile["lifetime"]
    earliesttimestamp=applydelta(now,-maxage,ageunit)
    for filename,timestamp in files:
      if timestamp<earliesttimestamp:
        print("Removing out of date backup: {}".format(filename))
        os.remove(os.path.join(os.path.join(dir,BACKUPDIR),filename)

