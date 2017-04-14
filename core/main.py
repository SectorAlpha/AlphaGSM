from utils.cmdparse import cmdparse
from server import Server, ServerError, server as servermodule
from . import multiplexer as mp
import subprocess as sp
import screen
import os
import traceback
from . import program
from sys import stderr, stdout
from textwrap import dedent

__all__ = ["main"]

DEBUG = bool(int(os.environ.get("ALPHAGSM_DEBUG", 0)))


def print_handled_ex(ex):
    """
    Print the exception or traceback to terminal depending on whether we're in debug mode
    """
    if DEBUG:
        traceback.print_exc()
    else:
        print(ex, file=stderr)


def main(name, args):
    """
    Main function called from the alphagsm executable

    name is the exectable name, whereas args are the arguments associated with the server

    args is a tuple of arguments used whilst executing the program, the infomation contains
      server names and commands to execute on those servers. 
         - Typically the first argument  is the server name (the one you want to operate on), 
           and this is followed by server related arguments.
           e.g "./alphagsm myserver mycommand"

         - If the first argument is a number, you then need to provide in spaces the names
           of servers you wish to operate on, 
           e.g  "./alphagsm 2 myservera myserverb mycommand"

         - You can also use * to denote all servers owned by the user
        
      On multiusers AlphaGSM setups, AlphaGSM can aquire a limited amount of "sudo" rights should 
      such a feature be requested. This opens up additional commands
         -  "user/server" for a user owned game server 
            e.g "./alphagsm someuser/someserver somecommand"
         - "./alphagsm */* somecommand" for all game servers running on the hardware 

    NB: we often refer the individual assigned server name itself as the server "tag"

    The main role of this function is to sanitize the command input from the user.
    """


    if len(args) == 1 and (args[0].lower() in ("-h", "-?", "--help")):
        args = ["*/*", "help"]
    #  if no arguments are called
    if len(args) < 1:
        print("You must specify at least a server to work on", file=stderr)
        print(file=stderr)
        help(name, None, full_help=True)
        return 2

    #  the first argument is either the server name, or the number of servers to run on
    servers = [args.pop(0)]
    #  if the first letter in server is a number, we want to work with a number of servers
    if servers[0].isdigit():
        #  how many servers?
        count = int(servers[0])
        #  seperate them from the arguments
        servers = args[:count]
        args = args[count:]
        #  we need at least 2 servers via this method
        if count < 1:
            print(
                "You must specify at least one server to work on",
                file=stderr
            )
            print(file=stderr)
            help(name, None)
            return 2
    #  prevent servers having similar names to commnds
    banned = set(("help", "create") + Server.default_commands)
    for s in servers:
        if s.lower() in banned:
            print(
                s, "is a banned server name as it's too similar to a command",
                file=stderr
            )
            print(file=stderr)
            help(name, None, full_help=True)
            return 2

    #  if no commands to run on the server(s)
    if len(args) < 1:
        print("You must specify at least a command to run", file=stderr)
        print(file=stderr)
        help(name, None, full_help=True)
        return 1

    #  since we popped the servers from the args variable earlier,
    #    we now get the command, and the arguments associated with the command
    #    this command is what we operate on the server (e.g start, stop)
    #
    #  At this point in time, servers are in the form of "servername" or 
    #    "username/servername" split_server_name returns (user,server)
    #     where user is None if we are that user
    #    
    #  spec is a single instance of "server" or "user/server", in which
    #     we put into a tuple (user,server)
    #
    #  in short, here were converting the list of servers containing
    #     list items of "server" or "user/server" into (user,server)
    #
    cmd, *args = args
    cmd = cmd.lower()
    servers = [
        #  split_server_name returns (User, server). User can be None
        #  if User = None, then we operate on own server.
        tuple(el if el != "all" else "*" for el in split_server_name(spec))
        for spec in servers
    ]

    #  now servers = [(user,server)] 
    #  [(*,*)] represents all users and all servers
    #  the help command for all servers owed by all users being called
    if len(servers) == 1 and servers[0] == ("*", "*") and cmd == "help":
        help(name, None, *args, file=stdout)
        return 0

    #  now we modify the server list even more
    #  TODO: WHY DO WE DO THIS`
    servers = [
        s for user, tag in servers for s in expand_server_star(user, tag, cmd)
    ]
    if len(servers) < 1:
        print("No servers found for", cmd, file=stderr)
        print(file=stderr)
        help(name, None)
        return 1

    #  run the command on multiple servers
    elif len(servers) > 1:
        if cmd == "list":
            return run_list_multi(name, servers, [cmd] + args)
        else:
            return run_multi(name, len(servers), servers, [cmd] + args)
    #  just operating on one server
    else: 
        return run_one(name, servers[0], cmd, args)
    return 0


def run_one(name, server, cmd, args):
    """
    Run a single command or list of commands on a single server
    """
    user, tag = server
    if user is not None:
        #  run the command for a server another user owns
        if cmd == "list":
            return run_list_multi(name, [server], [cmd] + args)
        else:
            return run_as(name, user, tag, [cmd] + args)
    else:
        #  are we making a new server?
        if cmd == "create":
            if len(args) < 1:
                print(
                    "Type of server to create is a required argument",
                    file=stderr
                )
                print(file=stderr)
                help(name, None, cmd)
                return 2
            try:
                server = Server(tag, args[0])
            except ServerError as ex:
                print("Can't create server", file=stderr)
                print_handle_dex(ex)
                print(file=stderr)
                help(name, None, cmd)
                return 1
            print("Server created", flush=True)
            if len(args) > 1:
                cmd, *args = args[1:]
                cmd = cmd.lower()
                if cmd != "setup":
                    print("Only setup can be called after create", file=stderr)
                    print(file=stderr)
                    help(name, None, cmd)
                    return 2
            else:
                cmd = None
                args = ()
        else:
            try:
                server = Server(tag)
            except ServerError as ex:
                print("Can't find server", file=stderr)
                print_handled_ex(ex)
                print(file=stderr)
                help(name, None)
                return 1
        if cmd is None or cmd == "help":
            help(name, server, *args, file = stdout, full_help=True)
        elif cmd == "list":
            print(tag)
        else:
            try:
                cmdargs = server.get_command_args(cmd)
            except cmdparse.OptionError as ex:
                print("Error parsing arguments and options", file=stderr)
                print_handled_ex(ex)
                print(file=stderr)
                help(name, server, cmd)
                return 2
            if cmdargs is None:
                print("Unknown command", file=stderr)
                print(file=stderr)
                help(name, server, cmd)
                return 2
            try:
                args, opts = cmdparse.parse(args, cmdargs)
            except cmdparse.OptionError as ex:
                print("Error parsing arguments and options", file=stderr)
                print_handled_ex(ex)
                print(file=stderr)
                help(name, server, cmd)
                return 2
            #  needed by activate and deactivate
            program.PATH = os.path.join(
                os.path.dirname(os.path.dirname(
                    os.path.realpath(os.path.abspath(__file__))
                )),
                "alphagsm"
            )
            try:
                server.run_command(cmd, *args, **opts)
                #  developers: be sure to check if command_functions dictionary
                #  has been filled, otherwise the error called here will make
                #  no sense
            except ServerError as ex:
                print("Error running Command", file=stderr)
                print_handled_ex(ex)
                return 1
            except Exception as ex:
                print("Error running command", file=stderr)
                print_handled_ex(ex)
                return 3
    return 0


def split_server_name(name):
    """
    This is used to select a server owned by a user
    
    name: 
       - if name is a string without "/", then this represents
          the server name, and thus this server is owned by
          the current user
       - if name is a string with "/" we split it, the left 
          hand side is the user name and the right hand side is
          the server owned by that user

    returns
         User, server

    if User = None, then we act upon the server owned by the current user
    """

    split = name.split("/")
    if len(split) == 1:
        #  server is owned by user
        return None, split[0]
    elif len(split) == 2:
        #  server is owned by another user
        #  split[0] = user, split[1] is the server
        return split[0], split[1]
    else:
        #  invalid input, raise error
        raise ServerError("Invalid server name. Only one / allowed")


def get_all_all_servers(command):
    if command in {"stop", "status", "message", "backup", "list"}:
        servers = list(screen.list_all_screens())
        if command == "stop":
            print("Saving server list", file=stderr)
            with open(".alphagsmserverlist", "w") as f:
                for server in servers:
                    f.write("{}\n".format(server))
        print("Using servers for '*/*':", *servers, file=stderr)
        return servers
    elif command == "start":
        servers = []
        with open(".alphagsmserverlist", "r") as f:
            for line in f:
                servers.append(line.strip())
        print("Using servers for '*/*':", *servers, file=stderr)
        return servers
    return []


def get_all_user_servers():
    """
    Loop over the datapath of the user
    Return     
    """

    try:
        servers = [
            (None, el[:-5])
            for el in os.listdir(servermodule.DATAPATH)
            if el.endswith(".json")
        ]
    except FileNotFoundError:
        print("No servers found for user", file=stderr)
        return []
    print(
        "Using servers for '*':", *(tag for user, tag in servers), file=stderr
    )
    return servers


def expand_server_star(user, tag, cmd):
    """
    inputs
       user: the user (None if we are using the current logged in users servers)
       tag: the server name
       cmd: the command or list of commands

    Output:
       A list of users and server tags turples
          [(user,server_tag)]
    """
   
    #  are we acting on all users, we can act on all users
    if user == "*":
        #  are we acting on all servers? 
        #  we don't know every server owned by a user trivially
        #  TODO allow this?
        if tag != "*":
            # if not acting on all servers, then this is ambiguous
            print("Error: Can't specify a server but '*' user")
            return ()
        else:
            #  get all users and servers
            return [split_server_name(s) for s in get_all_all_servers(cmd)]

    #  i.e we are acting on all of the servers owned by the user
    elif tag == "*" and user is None:
        return get_all_user_servers()
    #  otherwise don't change much
    else:
        return [(user, tag)]


def get_run_as_cmd(name, user, server, args, multi=False):
    return ["sudo", "-Hu", user] + get_run_cmd(name, server, args, multi = multi)


def get_run_cmd(name, server, args, multi=False):
    scriptpath = os.path.join(
        os.path.dirname(os.path.dirname(
            os.path.realpath(os.path.abspath(__file__))
        )),
        "alphagsm-internal"
    )
    return [scriptpath, "1" if multi else "0", name, server] + args


def run_as(name, user, server, args):
    ret = sp.call(get_run_as_cmd(name, user, server, args))
    print("Command finished with return status", ret, file=stderr)
    return ret


def run_list_multi(name, servers, args):
    finalret = 0
    for user, server in servers:
        if user is not None:
            cmd = get_run_as_cmd(name, user, server, args)
        else:
            cmd = get_run_cmd(name, server, args)
        proc = sp.Popen(cmd, stdout=sp.PIPE)
        output, _ = proc.communicate()
        output = [
            line.strip()
            for line in output.decode(stdout.encoding).splitlines()
            if line and not line.isspace()
        ]
        for el in output:
            if user is not None:
                print("{}/{}".format(user, el))
            else:
                print(el)
        if proc.returncode != 0:
            print(
                "Command finished with return status", proc.returncode,
                file=stderr
            )
            if finalret == 0 or finalret == proc.returncode:
                finalret = proc.returncode
            else:
                finalret = 10
    return finalret


def _internal_is_running(line):
    return line.decode().strip() == "#%AlphaGSM-INTERNAL%#"


def run_multi(name, count, servers, args):
    multi = mp.Multiplexer()
    for user, server in servers:
        if user is not None:
            cmd = get_run_as_cmd(name, user, server, args, True)
        else:
            cmd = get_run_cmd(name, server, args, True)
        mp.addtomultiafter(
            multi,
            (user + "/" if user is not None else "") + server,
                    _internal_is_running,
                    cmd,
                    stdin=sp.DEVNULL,
                    stdout=sp.PIPE,
                    stderr=sp.STDOUT
	    )
    multi.processall()
    retvals = list(multi.checkreturnvalues().values())
    if len(retvals) != len(servers):
        print("Warning: Not all servers have returned", file=stderr)
    if all(val == 0 for val in retvals):
        return 0
    retvalsnon0 = [val for val in retvals if val != 0]
    if all(val == retvalsnon0[0] for val in retvalsnon0):
        return retvalsnon0[0]
    else:
        return 10


def help(name, server, cmd=None, *, file=stderr, full_help=False):
    """
    The help function, which lists all of the commands used in AlphaGSM

    Parameters
    ------------
    server: The name of the server that was used to execute the command
    cmd : The command in question
    * : passomg  
    """
    if cmd is None:
        if full_help:
            print(
                "The Sector-Alpha Game Server Management Script (AlphaGSM)",
                file=file
            )
        print(file=file)
        print(name, "SERVER COMMAND [ARGS...]", file=file)
        print(name, "COUNT SERVER... COMMAND [ARGS...]", file=file)
        if full_help:
            print(dedent("""
                SERVER is the server or servers to process. If a server is
                specified as username/server then we use sudo to run as the
                relevant user. This is always possible as root but is up to sudo
                otherwise and may prompt for a password. The server can be the
                special forms "*", which means apply to all the current user's
                servers ("username/*" works too), or "*/*" which means run on a
                command dependent definition of "all servers". This last form is
                only available for a very limited set of commands.

                If the second calling form is specified there must be EXACTLY
                COUNT servers specified.
             
            """), file=file
            )

        print(dedent("""
        The available commands are:
          help [COMMAND] : Print a help message. Without a command print
                           this message or with a command print detailed help
                           for that command.
          create TYPE [setup ARGS] : Create a new server of the specified
                           type. If setup is specified then will call setup on
                           the new server immediately. ARGS is passed directly
                           on to setup so see there for the format and options
                           available.
          list : list the servers this is run on one per line. Useful for
                           checking what servers a wildcard matched or in
                           scripts to list the servers in a script processable
                           way.
        """), file=file)



        if server is None:
            for cmd in Server.default_commands:
                cmdparse.shorthelp(
                    cmd, Server.default_command_descriptions.get(cmd, None),
                    Server.default_command_args[cmd]
                )
        else:
            for cmd in server.get_commands():
                cmdparse.shorthelp(
                    cmd, server.get_command_description(cmd),
                    server.get_command_args(cmd)
                )
    else:
        if server is None:
            if cmd not in Server.default_commands:
                print("Unknown Command", file=file)
                print(file=file)
                help(name, server, file=file)
                return
            cmdparse.longhelp(
                cmd, Server.default_command_descriptions.get(cmd, None),
                Server.default_command_args[cmd]
            )
        else:
            if cmd not in server.get_commands():
                print("Unknown Command", file=file)
                print(file=file)
                help(name, server, file=file)
                return
            cmdparse.longhelp(
                cmd, server.get_command_description(cmd),
                server.get_command_args(cmd)
            )

    if full_help:
        print(dedent("""
            AlphaGSM Copyright (C) 2016 by Sector Alpha.
            Licensed under GPL v3.0. See the LISCENCE file for details.
            Developed by Cosmosquark and Staircase27. See the CREDITS file for a
            full list of contributors.

            A command line tool to download, manage and maintain game servers
            using simple and similar commands. See the README, future_plans and
            the changelog files for more details. Hosted and maintained on our
            github page https://github.com/SectorAlpha/AlphaGSM. Raise any issues
            or ask any questions on our github page, or contact
            cosmosquark@sector-alpha.net. Additionally check out the project
            wiki at http://wiki.sector-alpha.net/index.php?title=AlphaGSM
        """), file=file)
