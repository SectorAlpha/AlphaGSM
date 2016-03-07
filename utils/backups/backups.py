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
      if "replace_targets" in profiledata or "targets" not in newprofiledata:
        newprofiledata["targets"]=profiledata["targets"]
      else:
        newprofiledata["targets"]=newprofiledata["targets"]+profiledata["targets"]
    if "exclusions" in profiledata:
      if "replace_exclusions" in profiledata or "exclusions" not in newprofiledata:
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
  targetname=os.path.join(os.path.join(dir,BACKUPDIR),tag+" "+now.strftime(TIMESTAMPFORMAT)+".zip")
  try:
    sp.check_call(['zip','-ry',os.path.join('backup',datetime.datetime.now().isoformat())]+data['targets']+["-x"]+data["exclusions"],cwd=server.data['dir'])
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

