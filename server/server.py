import os
from . import data
from importlib import import_module
import screen
import time

__all__=["Server","ServerError"]

DATAPATH=os.path.expanduser("~/.samconf")
SERVERMODULEPACKAGE="gamemodules."

class ServerError(Exception):
  pass

class Server(object):
  default_commands=("setup","start","stop","status","message","connect","dump","set")
  default_command_args={"setup":([],[],False,[("n",["noask"],"Don't ask for input. Just fail if we can't cope","ask",None,False)]),
                        "start":([],[],False,[]),
                        "stop":([],[],False,[]),
                        "status":([],[],False,[("v",["verbose"],"Verbose status. argument is the level from 0 (normal) to 3 (max)","verbose","LEVEL",int)]),
                        "message":([("MESSAGE","The message to send",str)],[],False,[]),
                        "connect":([],[],False,[]),
                        "dump":([],[],False,[]),
                        "set":([("KEY","The key to set in the form of dot seperated elements",str),
                                ("VALUE","The value to set. Can be '[]' or '{}' to add a new node to the tree.",str)],[],False,[])}
  default_command_descriptions={}
  def __init__(self,name,module=None):
    self.name=name
    if module is not None:
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
      raise ServerError("Invalid module requested: "+self.data["module"])
    self.data["module"]=str(self.data["module"])
    if not self.data["module"].isalnum():
      raise ServerError("Invalid module requested: "+self.data["module"])
    try:
      self.module=import_module(SERVERMODULEPACKAGE+self.data["module"])
    except ImportError as ex:
      raise ServerError("Can't find module: "+self.data["module"],ex)
  
  def get_commands(self):
    return self.default_commands+self.module.commands

  def get_command_args(self,command):
    args=self.default_command_args.get(command,None)
    extra_args=self.module.command_args.get(command,None)
    if extra_args is not None:
      if args is None:
        args=extra_args
      else:
        if len(extra_args[0])>0:
          raise ServerException("Error in module: Can't add extra required arguments")
        if args[2] is not True:
          args=(args[0],args[1]+extra_args[1],extra_args[2],args[3]+extra_args[3])
        else:
          if len(extra_args[1])>0:
            raise ServerException("Error in module: Can't add extra arguments, already have a catch all argument")
          args=(args[0],args[1],args[2],args[3]+extra_args[3])
    return args
  def get_command_description(self,command):
    desc=self.default_command_descriptions.get(command,None)
    extra_desc=self.module.command_descriptions.get(command,None)
    if extra_desc is not None:
      if desc is None:
        desc=extra_desc
      else:
        desc=desc+"\n\n"+extra_desc
    return desc

  def run_command(self,command,*args,**kwargs):
    if command in self.default_commands:
      if command == "setup":
        self.setup(*args,**kwargs)
      elif command == "start":
        self.start(*args,**kwargs)
      elif command == "stop":
        self.stop(*args,**kwargs)
      elif command == "status":
        self.status(*args,**kwargs)
    elif command in self.module.commands:
      self.module.command_functions[command](self,*args,**kwargs)
    else:
      print("Unknown command '"+command+"' can't be executed. Please check the help")
      return 1

  def setup(self,*args,ask=True,**kwargs):
    args,kwargs=self.module.configure(self,ask,*args,**kwargs)
    self.module.install(self,*args,**kwargs)

  def start(self,*args,**kwargs):
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
    if not screen.check_screen_exists(self.name):
      print("Server isn't running as no screen session")
    else:
      print("Server is running as screen session exists")
      if verbose>0:
        self.module.status(self,*args,verbose=1,**kwargs)
