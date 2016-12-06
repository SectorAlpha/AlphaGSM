"""The core server class and the related ServerError exception

We also define in here the constants that specify the path where server data stores are saved 
(DATAPATH) and what package game server modules are searched for in (SERVERMODULEPACKAGE).

For details of how to write a game server module see the gamemodules module in this package."""
import os
from . import data
from importlib import import_module
import screen
import time
import crontab
from utils.cmdparse.cmdspec import CmdSpec, ArgSpec, OptSpec
from utils.settings import settings
from collections.abc import Mapping as MappingABC

__all__=["Server","ServerError"]

DATAPATH=os.path.expanduser(settings.user.getsection('server').get('datapath',os.path.join(settings.user.getsection('core',"~/.alphagsm"),"conf")))
SERVERMODULEPACKAGE=settings.system.getsection('server').get('servermodulespackage',"gamemodules.")

class ServerError(Exception):
  """An Exception thrown when there is an error with the server"""
  pass

def _findmodule(name):
  while True:
    name=str(name)
    if len(name)<2 and all((len(el)>0 and el.isalnum()) for el in name.split(".")):
      raise ServerError("Invalid module requested: "+self.data["module"])
    try:
      module=import_module(SERVERMODULEPACKAGE+name)
    except ImportError as ex:
      raise ServerError("Can't find module: "+name,ex)
    if not hasattr(module,'__file__'): # no filesystem path so must be a namespace path
      name=name+".DEFAULT"
      continue
    try:
      name=module.ALIAS_TARGET
    except AttributeError:
      return name,module

class Server(object):
  """An object that represents a game server
  
  Each instance of this class corresponds to a specific game server with a specified backend.
 

  Class Attributes: (DO NOT CHANGE)
    default_commands: the default list of commands that all servers handle.
    default_command_args: the default arguments for each of the commands specified in this package.
          More arguments can be specified by the backend module but these are required to be optional.
    default_command_description: the default description for each of the commands specified in this package.
          Extra description can be provided by the backend module which is appended to this description.
  
  Instance Attributes:
    self.name: the name of this server. DO NOT CHANGE
    self.module: the module object for the backend of this server. DO NOT CHANGE
    self.data: the backend data store for this server. DO NOT REPLACE
  """
    
  default_commands=("setup","start","stop","activate","deactivate","status","message","connect","dump","set","backup")
  default_command_args={"setup":CmdSpec(options=(OptSpec("n",["noask"],"Don't ask for input. Just fail if we can't cope","ask",None,False),)),
                        "start":CmdSpec(),
                        "stop":CmdSpec(),
                        "activate":CmdSpec(options=(OptSpec("d",["delay"],"Delay starting the server just setup the crontab","start",None,False),)),
                        "deactivate":CmdSpec(options=(OptSpec("d",["delay"],"Delay stopping the server just remove the crontab","stop",None,False),)),
                        "status":CmdSpec(options=(OptSpec("v",["verbose"],"Verbose status. argument is the level from 0 (normal) to 3 (max)","verbose","LEVEL",int),)),
                        "message":CmdSpec(requiredarguments=(ArgSpec("MESSAGE","The message to send",str),)),
                        "connect":CmdSpec(),
                        "dump":CmdSpec(),
                        "set":CmdSpec(requiredarguments=(ArgSpec("KEY","The key to set in the form of dot seperated elements",str),),
                                      optionalarguments=(ArgSpec("VALUE","The value to set. New nodes in the structure will be created as needed. "
                                                                 "Exactly how many values can be specified is KEY dependant.",str),),repeatable=True),
                        "backup":CmdSpec()}
  default_command_descriptions={"setup":"Setup the game server.\nThis will include processing the required settings,"
                                        " downloading or copying any needed files and doing any setup task so that a"
                                        " 'start' should work.\nIf noask is specified then this may fail if extra "
                                        "game server dependant settings are not provided.",
                                "start":"Start the server.",
                                "stop":"Stop the server.",
                                "activate":"Set the server to restart on reboots and start now unless --delay is specified.",
                                "deactivate":"Stop the server from restarting on reboots and stop now unless --delay is specified.",
                                "status":"Check the status of the server. At the minimum will report if the server is running.",
                                "message":"Message the server. By default sends the message to all users.",
                                "connect":"Connect to the server's console session.",
                                "dump":"Dump the servers data store.",
                                "set":"Set a parameter in data store to a new value.\nFor keys that index into lists the special entry 'APPEND' my be used to create a new "
                                    "entry at the end of the list. Also for some keys value 'DELETE' is a value that causes the entry to be deleted.\n\n"
                                    "Which values are changable is game module dependent",
                                "backup":"Backup the game server"}
  def __init__(self,name,module=None):
    """Initialise this Server object.
    
    If module is not None this is a new Server so initialise it with a data store containing
    only the module name otherwise load the data from the data store and use the module specified there.
    
    Raises a ServerError if we can't load the data store or if the module isn't specified or can't be loaded.
    """
    self.name=name
    if module is not None:
      if not os.path.isdir(DATAPATH):
        try:
          os.makedirs(DATAPATH)
        except OSError:
          raise ServerError("Data Path doesn't exist and can't create it",DATAPATH)
      self.data=data.JSONDataStore(os.path.join(DATAPATH,name+".json"),{"module":module})
      try:
        self.data.save()
      except IOError as ex:
        raise ServerError("Error saving initial data",ex)
    else:
      try:
        self.data=data.JSONDataStore(os.path.join(DATAPATH,name+".json"))
      except (IOError,data.DataError) as ex:
        raise ServerError("Error reading data",ex)
    if "module" not in self.data:
      raise ServerError("Invalid data store: No module specified")
    truename,self.module=_findmodule(self.data["module"])
    if truename!=self.data["module"]:
      print("Module has been redirected. Actual module is '"+truename+"'. Saving to data store.")
      self.data["module"]=truename
      self.data.save()
  
  def get_commands(self):
    """Get a list of all the commands available for this server"""
    return self.default_commands+self.module.commands

  def get_command_args(self,command):
    """Get the full argument spec for the command specified on this server"""
    args=self.default_command_args.get(command,None)
    extra_args=self.module.command_args.get(command,None)
    if args is None:
      return extra_args
    return args.combine(extra_args)

  def get_command_description(self,command):
    """Get the complete description for the command specified for this server"""
    desc=self.default_command_descriptions.get(command,None)
    extra_desc=self.module.command_descriptions.get(command,None)
    if extra_desc is not None:
      if desc is None:
        desc=extra_desc
      else:
        desc=desc+"\n\n"+extra_desc
    return desc

  def run_command(self,command,*args,**kwargs):
    """Run the specified command with the specified arguments on this server
    
    This raises ServerError if the command can't be found or the server state isnt valid
    for the requested command (e.g. stop command on a server that isn't running).

    It can also raise AttributeError if the backend modules doesn't provide some of the
    required functions. It can also raise other Exceptions if the arguments don't match those
    required by either this or the backend module
    """
    if command in self.default_commands:
      if command == "setup":
        self.setup(*args,**kwargs)
      elif command == "start":
        self.start(*args,**kwargs)
      elif command == "stop":
        self.stop(*args,**kwargs)
      elif command == "activate":
        self.activate(*args,**kwargs)
      elif command == "deactivate":
        self.deactivate(*args,**kwargs)
      elif command == "status":
        self.status(*args,**kwargs)
      elif command == "message":
        self.module.message(self,*args,**kwargs)
      elif command == "connect":
        self.connect(*args,**kwargs)
      elif command == "dump":
        self.dump(*args,**kwargs)
      elif command == "set":
        self.doset(*args,**kwargs)
      elif command == "backup":
        self.module.backup(self,*args,**kwargs)
    elif command in self.module.commands:
      self.module.command_functions[command](self,*args,**kwargs)
    else:
      raise ServerError("Unknown command '"+command+"' can't be executed. Please check the help")

  def setup(self,*args,ask=True,**kwargs):
    """Setup this server. Once this returns the server should be ready to start."""
    args,kwargs=self.module.configure(self,ask,*args,**kwargs)
    self.module.install(self,*args,**kwargs)

  def start(self,*args,**kwargs):
    """Start a server. Won't start it if the server is already running."""
    if screen.check_screen_exists(self.name):
      raise ServerError("Error: Can't start server that is already running")
    try:
      prestart=self.module.prestart
    except AttributeError:
      pass
    else:
      prestart(*args,**kwargs)
    cmd,cwd=self.module.get_start_command(self,*args,**kwargs)
    screen.start_screen(self.name,cmd,cwd=cwd)
    try:
      poststart=self.module.poststart
    except AttributeError:
      pass
    else:
      poststart(*args,**kwargs)

  def stop(self,*args,**kwargs):
    """Stop the server. If the server can't be stopped even after multiple attempts then raises a ServerError"""
    if not screen.check_screen_exists(self.name):
      raise ServerError("Error: Can't stop a server that isn't running")
    jmax=5
    try:
      jmax=min(jmax,self.module.max_stop_wait)
    except AttributeError:
      pass
    print("Will try and stop server for "+str(jmax)+" minutes")
    for j in range(jmax):
      self.module.do_stop(self,j,*args,**kwargs)
      for i in range(6):
        if not screen.check_screen_exists(self.name):
          return # session doesn't exist so success
        time.sleep(10)
      if not screen.check_screen_exists(self.name):
        return
      print("Server isn't stopping after "+str(j+1)+" minutes")
    print("Killing Server")
    screen.send_to_screen(self.name,["quit"])
    time.sleep(1)
    if screen.check_screen_exists(self.name):
      raise ServerError("Error can't kill server")
  
  def status(self,*args,verbose=0,**kwargs):
    """Print the status of the server. At the least shows if there is a server screen session running"""
    if not screen.check_screen_exists(self.name):
      print("Server isn't running as no screen session")
    else:
      print("Server is running as screen session exists")
      if verbose>0:
        self.module.status(self,verbose,*args,**kwargs)

  def connect(self):
    """Connect to the screen session to manually interact with the server"""
    screen.connect_to_screen(self.name)

  def dump(self):
    """Dump of the data in the data store"""
    print(self.data.prettydump())

  def doset(self,key,*args,**kwargs):
    """Set a value in the data store. The value will be check and post set actions may be run"""
    types,key=_parsekey(key)
    value=self.module.checkvalue(self,key,*args,**kwargs)
    data=self.data
    for t,el in zip(types[1:],key[:-1]):
      if el is None:
        print("Appending",el,t)
        data.append(t())
        data=data[-1]
      else:
        if isinstance(data,MappingABC) and el not in data:
          print("Adding as absent",el,t)
          data[el]=t()
        data=data[el]
    if value == "DELETE":
      del data[key[-1]]
    elif key[-1] is None:
      data.append(value)
    else:
      data[key[-1]]=value
    try:
      fn=self.module.postset
    except AttributeError:
      pass
    else:
      fn(server,key,*args,**kwargs)
    self.data.save()

  def activate(self,start=True):
    """Activate the server by enabling it in crontab and optionally starting it if not already running"""
    from core import program
    programpath=program.PATH
    ct=crontab.CronTab(user=True)
    jobs=((job,_parsecmd(job.command.split())) for job in ct if job.is_enabled() and job.slices.special=="@reboot" and job.command.startswith(programpath))
    jobs=[(job,cmd[1]) for job,cmd in jobs if cmd[0]==programpath and cmd[2:]==["start"]]
    if any(self.name in servers for job,servers in jobs):
      print("Server is already active. Can't activate again")
    elif len(jobs)>0:
      job,servers=jobs[0]
      servers.append(self.name)
      job.command=programpath+" "+str(len(servers))+" "+" ".join(servers)+" start"
      ct.write()
    else:
      ct.new(command=programpath+" "+self.name+" start").every_reboot()
      ct.write()
    if start and not screen.check_screen_exists(self.name):
      self.start()

  def deactivate(self,stop=True):
    """Activate the server by disabling it in crontab and optionally stopping it if it is running"""
    from core import program
    programpath=program.PATH
    if stop and screen.check_screen_exists(self.name):
      self.stop()
    ct=crontab.CronTab(user=True)
    jobs=((job,_parsecmd(job.command.split())) for job in ct if job.is_enabled() and job.slices.special=="@reboot" and job.command.startswith(programpath))
    jobs=[(job,cmd[1]) for job,cmd in jobs if cmd[0]==programpath and self.name in cmd[1] and cmd[2:]==["start"]]
    if len(jobs)==0:
      print("Server isn't active. Can't deactivate")
    else:
      for job,servers in jobs:
        if len(servers)==1:
          ct.remove(job)
        else:
          servers.remove(self.name)
          job.command=programpath+" "+str(len(servers))+" "+" ".join(servers)+" start"
      ct.write()

def _parsekeyelement(el):
  if el == "APPEND":
    return list,None
  elif el.isdigit():
    return list,int(el)
  else:
    return dict,str(el)

def _parsekey(key):
  return zip(*(_parsekeyelement(el) for el in key.split(".")))

def _parsecmd(cmd):
  if cmd[1].isdigit():
    count=int(cmd[1])
    return [cmd[0],cmd[2:2+count]]+cmd[2+count:]
  return [cmd[0],[cmd[1]]]+cmd[2:]
