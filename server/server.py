import os
from . import data
from importlib import import_module

__all__=["Server","ServerError"]

DATAPATH=os.path.expanduser("~/.samconf")
SERVERMODULEPACKAGE="gamemodules."

class ServerError(Exception):
  pass

class Server(object):
  default_commands=("setup","start","stop","status","message","connect","dump","set")
  default_command_args={"setup":([],[],None,[("n",["noask"],"Don't ask for input. Just fail if we can't cope","ask",False)]),
                        "start":([],[],None,[]),
                        "stop":([],[],None,[]),
                        "status":([],[],None,[]),
                        "message":([("MESSAGE","The message to send",str)],[],None,[]),
                        "connect":([],[],None,[]),
                        "dump":([],[],None,[]),
                        "set":([("KEY","The key to set in the form of a dot seperated elements",str),
                                ("VALUE","The value to set. Can be '[]' or '{}' to add a new node to the tree.",str)],[],None,[])}
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
          raise ServerException("Can't add extra required arguments")
        if args[2] is None:
          args=(args[0],args[1]+extra_args[1],extra_args[2],args[3]+extra_args[3])
        else:
          if len(extra_args[1])>0:
            raise ServerException("Can't add extra arguments, already have a catch all argument")
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

  def run_command(command,*args,**kwargs):
    if command in self.default_commands:
      if command == "setup":
         return self.setup(*args,**args)
      elsif
    elif command in self.module.commands:
      return self.module.command_functions[command](self,*args,**kwargs)
    else:
      print(("Unknown command '"+command+"' can't be executed. Please check the help"))
      return 1

  def setup(self,*args,ask=True,**kwargs):
    args,kwargs=self.module.initialise(self,ask,*args,**kwargs)
    self.module.install(self,*args,**kwargs)
    self.module.postinstall(self,*args,**kwargs)
