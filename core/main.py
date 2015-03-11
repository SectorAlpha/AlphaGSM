from . import cmdparse
from server import Server,ServerError
from . import multiplexer as mp
import subprocess as sp
import os

__all__=["main"]

def main(name,args):
  if len(args)<1:
    print("You must specify at least a server to work on")
    print()
    help(name,None)
    return 2
  count=1
  server=args.pop(0)
  if server.isdigit():
    count=int(server)
    server=args[:count]
    args=args[count:]
  if count<1:
    print("You must specify at least a server to work on")
    print()
    help(name,None)
    return 2
  if len(args)<1:
    print("You must specify at least a command to run")
    print()
    help(name,None)
    return 1
  cmd,*args=args
  cmd=cmd.lower()
  if count==1 and server == "*" and cmd == "help":
    help(name,None,*args)
    return 0
  if server == "*":
    count,server=getallservers(cmd)
  if count<1:
    print("You must specify at least a server to work on")
    print()
    help(name,None)
    return 2
  elif count>1:
    runmulti(name,count,server,[cmd]+args)
  else:
    user,server=splitservername(server)
    if user is not None:
      runas(name,user,server,[cmd]+args)
    else:
      if cmd == "create":
        if len(args)<1:
          print("Type of server to create is a required argument")
          print()
          help(name,None,cmd)
          return 2
        try:
          server=Server(server,args[0])
        except ServerError as ex:
          print("Can't create server")
          print(ex)
          print()
          help(name,None,cmd)
          return 1
        cmd=None
        if len(args)>1:
          cmd,*args=args[1:]
          cmd=cmd.lower()
        if cmd!="setup":
          print("Only setup can be called after create")
          return 2
      else:
        try:
          server=Server(server)
        except ServerError as ex:
          print("Can't find server")
          print(ex)
          print()
          help(name,None)
          return 1
      if cmd is None or cmd == "help":
        help(name,server,*args)
      else:
        try:
          args,opts=cmdparse.parse(args,server.get_command_args(cmd))
        except cmdparse.OptionError as ex:
          print("Error parsing arguments and options")
          print(ex)
          print()
          help(name,server,cmd)
          return 2
        try:
          server.run_command(cmd,*args,**opts)
        except ServerError as ex:
          print(ex)
          return 1
        except Exception as ex:
          print("Error running command")
          print(ex)
          return 1
  return 0

def splitservername(server):
  slash=server.find("/")
  if slash<0:
    return None,server
  else:
    return server[:slash],server[slash+1:]

def getallservers(command):
  return 0,[]

def getrunascmd(name,user,server,args):
  return ["sudo","-Hu",user]+getruncmd(name,server,args)

def getruncmd(name,server,args):
  scriptpath=os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(os.path.abspath(__file__)))),"alphagsm-internal")
  return [scriptpath,name,server]+args

def runas(name,user,server,args):
  ret=sp.call(getrunascmd(name,user,server,args))
  print("Command finished with return status",ret)

def _internalisrunning(line):
  return line.decode().strip()=="#%AlphaGSM-INTERNAL%#"

def runmulti(name,count,servers,args):
  multi=mp.Multiplexer()
  for rawserver in servers:
    user,server=splitservername(rawserver)
    if user is not None:
      cmd=getrunascmd(name,user,server,args)
    else:
      cmd=getruncmd(name,server,args)
    mp.addtomultiafter(multi,rawserver,_internalisrunning,cmd,stdin=sp.DEVNULL,stdout=sp.PIPE,stderr=sp.STDOUT)
  multi.processall()

def help(name,server,cmd=None,*_):
  if cmd is None:
    print("The Sector-Alpha Game Server Management Script (AlphaGSM)")
    print()
    print(name+" SERVER COMMAND [ARGS...]")
    print(name+" COUNT SERVER... COMMAND [ARGS...]")
    print(
"""
SERVER is the server or servers to process. The server can be the special form
"*" which means apply to "all" servers. Exactly what all servers means is 
command dependant.

If the second calling form is specified there must be EXACTLY COUNT servers
specified.

If a server is specified as username/tag then we use sudo to run it as the
relevent user. This is always possible as root but is up to sudo otherwise
and may prompt for a password.

The available commands are:
  help [COMMAND] : Print a help message. Without a command print this message
        or with a command print detailed help for that command.
  create TYPE [setup ARGS] : Create a new server of the specified type. If setup
        is specified then will call setup on the new server immediately. ARGS is
        passed directly on to setup so see there for the format and options
        available""")
    if server is None:
      for cmd in Server.default_commands:
        cmdparse.shorthelp(cmd,Server.default_command_descriptions.get(cmd,None),Server.default_command_args[cmd])
    else:
      for cmd in server.get_commands():
        cmdparse.shorthelp(cmd,server.get_command_description(cmd),server.get_command_args(cmd))
  else:
    if server is None:
      if cmd not in Server.default_commands:
        print("Unknown Command")
        print()
        help(name,server)
        return
      cmdparse.longhelp(cmd,Server.default_command_descriptions.get(cmd,None),Server.default_command_args[cmd])
    else:
      if cmd not in server.get_commands():
        print("Unknown Command")
        print()
        help(name,server)
        return
      cmdparse.longhelp(cmd,server.get_command_description(cmd),server.get_command_args(cmd))
   
    
