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
from utils.cmdparse.cmdspec import CmdSpec,OptSpec,ArgSpec
from utils import backups
import random

_confpat=re.compile(r"\s*([^ \t\n\r\f\v#]\S*)\s*=(?:\s*(\S+))?(\s*)\Z")
def updateconfig(filename,settings):
    lines=[]
    if os.path.isfile(filename):
        settings=settings.copy()
        with open(filename,"r") as f:
            for l in f:
                m=_confpat.match(l)
                if m is not None and m.group(1) in settings:
                    lines.append(m.expand(r"\1="+settings[m.group(1)]+r"\3"))
                    del settings[m.group(1)]
                else:
                    lines.append(l)
    for k,v in settings.items():
        lines.append(k+"="+v+"\n")
    print(lines)
    with open(filename,"w") as f:
        f.write("".join(lines))

# required tuple
commands=("op","deop")

# required
# dictionary command_args 
#   key = command name
#   value = CmdSpec(optional argument tuple=(Argument, description, type), 
#      options=(Optspec( shortform, longform, description, keyword to store option, default value, store value if true, else run function))
command_args={"setup":CmdSpec(optionalarguments=(ArgSpec("PORT","The port for the server to listen on",int),ArgSpec("DIR","The Directory to install minecraft in",str),),
                                                            options=(OptSpec("l",["eula"],"Mark the eula as read","eula",None,True),)),
                            "op":CmdSpec(requiredarguments=(ArgSpec("USER","The user[s] to op",str),),repeatable=True),
                            "deop":CmdSpec(requiredarguments=(ArgSpec("USER","The user[s] to deop",str),),repeatable=True),
                            "message":CmdSpec(optionalarguments=(ArgSpec("TARGET","The user[s] to send the message to. Sends to all if none given.",str),),repeatable=True,
                                            options=(OptSpec("p",["parse"],"Parse the message for selectors (otherwise prints directly).","parse",None,True),)),
                            "backup":CmdSpec(optionalarguments=(ArgSpec("PROFILE","Do a backup using the specified profile",str),),
                                                             options=(OptSpec("a",["activate"],"Activate regular backups. Valid values for frequency are 'daily', 'weekly', 'monthly' and 'yearly' or 'none' to disable",'activate',"FREQUENCY",str),
                                                                             OptSpec("d",["deactivate"],"Deactivate regular backups. Equivelent to --activate none",'activate',None,'none'),
                                                                             OptSpec("w",["when"],"When should the regular backups take place. Valid format is 'hour[:minute][ DATE]' where DATE is the day of the week (3 letter names accepted) for "
                                                                                     "weekly, the day of the month for monthly, the day and month (3 letter names accepted for month) for yearly backups and not allowed for daily backups",'when','WHEN',str)))}

# required
command_descriptions={'set':"The available keys to set are:\texe_name: (1 value) the name of the jar file to execute\n\tbackup.profiles.PROFILENAME.targets: (many values) the "
                                                        "targets to include in a backup using the specified profile\n\tbackup.profiles.PROFILENAME.exclusions: (many values) patterns that match files to "
                                                        "exclude from a backup using the specified profile\n\tbackup.profiles.PROFILENAME.base: (one value) the name of a profile that this profile extends\n\t"
                                                        "backups.profiles.PROFILENAME.replace_targets and backups.profiles.PROFILENAME.replace_exclusions: (one value: on/off) Should the relevent entry "
                                                        "replace the base rather than extend the bases value\n\tbackups.profiles.PROFILENAME.lifetime: (two values: length year,month,week,day) How long "
                                                        "the backups should be kept for\n\tbackups.schedule.INDEX/APPEND: (3 values: profile timelength timeunit) how long there should be between backups "
                                                        "using that profiles"}
command_functions={} # will have elements added as the functions are defined

def configure(server,ask,port=None,dir=None,*,eula=None,exe_name="minecraft_server.jar"):
    """
    This function creates the configuration details for the minecraft server
    
    inputs:
        server: the server object
        ask: whether to request details (e.g port) from the user
        dir: the server installation dir
        *: All arguments after this are keyword only arguments
        eula: whether the user agrees to sign the eula
        exe_name: the executable name of the server
    """
    # do we have backup data already? if not initialise the dictionary
    if 'backup' not in server.data:
        server.data['backup']={}
    if 'profiles' not in server.data['backup']:
        server.data['backup']['profiles']={}
    # if no backup profile exists, create a basic one
    if len(server.data['backup']['profiles'])==0:
        # essentially, the world, server properties and the root level json files are the best ones to back up. This can be configured though in the backup setup
        server.data['backup']['profiles']['default']={'targets':['world','server.properties','whitelist.json','ops.json','banned-ips.json','banned-players.json']}
    if 'schedule' not in server.data['backup']:
        server.data['backup']['schedule']=[]
    if len(server.data['backup']['schedule'])==0:
        # if default does not exist, create it
        profile='default'
        if profile not in server.data['backup']['profiles']:
            profile=next(iter(server.data['backup']['profiles']))
        # set the default to never back up
        server.data['backup']['schedule'].append((profile,0,'days'))
    
    # assign the port to the server
    if port is None and "port" in server.data:
        port=server.data["port"]
    if ask:
        while True:
            inp=input("Please specify the port to use for this server: "+(str(port) if port is not None else "")).strip()
            if port is not None and inp == "":
                break
            try:
                port=int(inp)
            except ValueError as v:
                print(inp+" isn't a valid port number")
                continue
            break
    if port is None :
        raise ValueError("No Port")
    server.data["port"]=port

    # assign the installation directory
    if dir is None:
        if "dir" in server.data and server.data["dir"] is not None:
            dir=server.data["dir"]
        else:
            # if no directory is assigned, set it to the users home area
            dir=os.path.expanduser(os.path.join("~",server.name))
        if ask:
            # set a custom location to install the directory?
            inp=input("Where would you like to install the minecraft server: ["+dir+"] ").strip()
            if inp!="":
                dir=inp
    server.data["dir"]=dir

    # lets sign the eula
    if eula is None:
        if ask:
            eula=input("Please confirm you have read the eula (y/yes or n/no): ").strip().lower() in ("y","yes")
        else:
            eula=False

    # if exe_name is not asigned, use the function default one
    if not "exe_name" in server.data:
        server.data["exe_name"] = exe_name
    server.data.save()

    # required since we are returning args and kwargs.
    # essentially the default version of this line would be return (),{}
    return (),{"eula":eula}

# install requires the server object. you also feed in the arguments (*) and the kwargs {} from the previous return statement
# as seen at the end of the configure function.
def install(server,*,eula=False):
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    mcjar=os.path.join(server.data["dir"],server.data["exe_name"])
    if not os.path.isfile(mcjar):
        raise ServerError("Can't find server jar ({}). Please place the files in the directory and/or update the 'exe_name' then run setup again".format(mcjar))
    server.data.save()

    eulafile=os.path.join(server.data["dir"],"eula.txt")
    configfile=os.path.join(server.data["dir"],"server.properties")
    if not os.path.isfile(configfile) or (eula and not os.path.isfile(eulafile)): # use as flag for has the server created it's files
        print("Starting server to create settings")
        try:
            ret=sp.check_call(["java","-jar",server.data["exe_name"],"nogui"],cwd=server.data["dir"],shell=False,timeout=20)
        except sp.CalledProcessError as ex:
            print("Error running server. Java returned status: "+ex.returncode)
        except sp.TimeoutExpired as ex:
            print("Error running server. Process didn't complete in time")
    updateconfig(configfile,{"server-port":str(server.data["port"])})
    if eula:
        updateconfig(eulafile,{"eula":"true"})
        
def get_start_command(server):
    return ["java","-jar",server.data["exe_name"],"nogui"],server.data["dir"]

def do_stop(server,j):
    screen.send_to_server(server.name,"\nstop\n")

def status(server,verbose):
    pass

def message(server,msg,*targets,parse=False):
    if len(targets)<1:
        targets=["@a"]
    if parse and "@" in msg:
        msglist=[]
        pat=re.compile(r"([^@]*[^\\])?(@.(?:\[[^\]]+\])?)")
        while True:
            match=pat.match(msg)
            if match is None:
                break
            if match.group(1) is not None:
                msglist.append(match.group(1)) # group is optional
                # nothing stopping two selectors straight after each other
            msglist.append({"selector":match.group(2)})
            msg=msg[match.end(0):]
        msglist.append(msg)
        msgjson=json.dumps(msglist)
    else:
        msgjson=json.dumps({"text":msg})
    cmd="\n".join("tellraw "+target+" "+msgjson for target in targets)
    print(cmd)
    screen.send_to_server(server.name,"\n"+cmd+"\n")

def checkvalue(server,key,*value):
    if key[0] == "TEST":
        return value[0]
    if key == ("exe_name",):
        if len(value)!=1:
            raise ServerError("Only one value supported for 'exe_name'")
        return value[0]
    if key[0] == ("backup"):
        try:
            return backups.checkdatavalue(server.data.get("backup",{}),key[1:],*value)
        except backups.BackupError as ex:
            raise ServerError(ex)
    raise ServerError("{} invalid key to set".format(".".join(str(k) for k in key)))

def _parsewhen(frequency,when):
    if when is None:
        time,rest=None,None
    else:
        time,rest=(when.split(None,2)+[None,None])[:2]
    if time is None:
        hour,minute=None,None
    else:
        hour,minute=(time.split(":")+[None,None])[:2] # ditch any seconds provided. If no : treat as am hour
    if hour is None:
        hour = random.randint(2,6)
    if minute is None:
        minute = random.randint(0,59)
    if frequency == "daily":
        return minute,hour,None,None,None
    elif frequency == "weekly":
        if rest is None:
            rest = random.randint(0,6)
        return minute,hour,None,None,rest
    elif frequency == "monthly":
        if rest is None:
            rest = random.randint(1,28)
        return minute,hour,rest,None,None
    else: # frequency == "yearly"
        if rest is None:
            day,month = None,None
        else:
            day,month = (rest.split("/")+[None,None])[:2] # ditch any year provided. If no / treat as day
        if day is None:
            day = random.randint(1,28)
        if month is None:
            month = random.randint(1,12)
        return minute,hour,day,month,None

def backup(server,profile=None,*,activate=None,when=None):
    if activate is None:
        dobackup(server,profile)
    else:
        if profile is not None:
            raise ServerError("Can't specify a profile if activating. Edit the backup schedule to change what backups are done when")
        if activate not in ("weekly","monthly","yearly","daily","none"):
            raise ServerError("Invalid frequency for backups. Options are 'yearly', 'monthly', 'weekly' or 'daily'")
        import crontab
        from core import program
        programpath=program.PATH
        ct=crontab.CronTab(user=True)
        jobs=((job,job.command.split()) for job in ct if job.is_enabled() and job.command.startswith(programpath))
        jobs=[job for job,cmd in jobs if cmd[0]==programpath and server.name == cmd[1] and cmd[2:]==["backup"]]
        if activate == "none":
            if len(jobs)==0:
                raise ServerError("backups aren't active. Can't deactivate")
            else:
                for job in jobs:
                    ct.remove(job)
        else:
            for job in jobs:
                ct.remove(job)
            job=ct.new(command=programpath+" "+server.name+" backup")
            if not job.setall(*_parsewhen(activate,when)):
                print("Error parsing time spec")
                if job.slices[0].parts==[]:
                    job.slices[0].parse(random.randint(0,59))
                if job.slices[1].parts==[]:
                    job.slices[1].parse(random.randint(2,6))
                if activate in ("monthly","yearly") and job.slices[2].parts==[]:
                    job.slices[2].parse(random.randint(1,28))
                if activate == "yearly" and job.slices[3].parts==[]:
                    job.slices[3].parse(random.randint(1,12))
                if activate == "weekly" and job.slices[4].parts==[]:
                    job.slices[4].parse(random.randint(0,6))
            for slice in job.slices:
                slice.parse(slice.render(True))
            print("Job schedule set to {}".format(job.slices))
        ct.write()
        
def dobackup(server,profile=None):
    if screen.check_screen_exists(server.name):
        screen.send_to_server(server.name,"\nsave-off\nsave-all\n")
        time.sleep(30)
    try:
        backups.backup(server.data["dir"],server.data['backup'],profile)
    except backups.BackupError as ex:
        raise ServerError("Error backing up server: {}".format(ex))
    finally:
        if screen.check_screen_exists(server.name):
            screen.send_to_server(server.name,"\nsave-on\nsave-all\n")

def op(server,*users):
    for user in users:
        screen.send_to_server(server.name,"\nop "+user+"\n")
command_functions["op"]=op

def deop(server,*users):
    for user in users:
        screen.send_to_server(server.name,"\ndeop "+user+"\n")
command_functions["deop"]=deop
