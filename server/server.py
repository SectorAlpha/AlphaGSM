import os
from  .. import data
from importlib import import_module

__all__=["Server"]

DATAPATH=os.path.expanduser("~/.samconf")
SERVERMODULEPACKAGE="gamemodules."

def _addandreturn(s,i):
  s.add(i)
  return i

class Server(object):
  default_commands=("create","start","stop")
  default_command_args={"create":(1,0,[("game","The name of the game to install. Will be prompted for if not given",str)],[],
                        "start":()}
  def __init__(self,name):
    self.name=name
    self.data=data.JSONDataStore(os.path.join(DATAPATH,name+".json"))
    if "module" in self.data:
      self.data["module"]=str(self.data)
      if not self.data["module"].isalnum():
        del self.data["module"]
    if "module" in self.data:
      self.module=import_module(SERVERMODULEPACKAGE+self.data["module"])
    else:
      self.module=None
  def is_valid(self):
    return self.module is None
  
  def get_commands(self):
    if 
    commands=self.default_commands
    if self.module is not None:
      try:
        commands+=tuple(self.module.commands)
      except AttributeError:
        pass
    tmp=set()
    return tuple(_addandreturn(tmp,cmd) for cmd in commands if cmd not in tmp)

  def get_command_args(self,command):
    #TODO: work out how to represent the arguments and combine for the different cases
   

  def run_command(command,*args,**kwargs):
    if self.module is None
      if command !="create":
        return create(*args,**kwargs)
      else:
        print "Only 'create' is valid without a created instance to work on"
        return 1
    else:
      if command in self.default_commands:
        #TODO: implement code for each command
      else if command in self.module.commands:
        return self.module.command_functions[command](self,*args,**kwargs)
      else:
        print "Unknown command '"+command+"' can't be executed. Please check the help"
        return 1


