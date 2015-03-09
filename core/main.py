from . import cmdparse
from server import Server,ServerError

__all__=["main"]

def main(name,args):
  if len(args)<1:
    print("You must specify at least a server to work on")
    print()
    help(name,None)
    return
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
    return
  if len(args)<1:
    print("You must specify at least a command to run")
    print()
    help(name,None)
    return
  cmd,*args=args
  if count==1 and server == "*" and cmd == "help":
    help(name,None,*args)
    return
  if server == "*":
    count,servers=getallservers(command)
  if count<1:
    print("You must specify at least a server to work on")
    print()
    help(name,None)
    return
  elif count>1:
    runmulti(name,count,servers,[command]+args)
  else:
    user,server=splitservername(server)
    if user is not None:
      runas(name,user,server,[command]+args)
    else:
      try:
        server=Server(server)
      except ServerError as ex:
        print("Can't find server")
        print(ex)
        print()
        help(name,None)
        return
      if cmd == "help":
        help(name,server,*args)
      else:
        try:
          args,opts=cmdparse.parse(args,server.get_command_args(cmd))
        except cmdparse.OptionError as ex:
          print("Error parsing arguments and options")
          print(ex)
          print()
          help(name,server,cmd)
          return
        try:
          server.run_command(cmd,*args,**opts)
        except ServerError as ex:
          print(ex)
        except Exception as ex:
          print("Error running command")
          print(ex)

def splitservername(server):
  slash=server.find("/")
  if slash<0:
    return None,server
  else:
    return server[:slash],server[slash+1:]

def getallservers(command):
  return 0,[]

def runas(name,user,server,args):
  pass

def runmulti(name,count,server,args):
  pass

def help(name,server,cmd=None,*_):
  if cmd is None:
    print("The Sector-Alpha Game server management script")
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
   
    
