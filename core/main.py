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


def printhandledex(ex):
    """
    Print the traceback or error to terminal depending on whether we're in debug mode
    """
    if DEBUG:
        traceback.print_exc()
    else:
        print(ex, file=stderr)


def main(name, args):
    """
    Main function called from the alphagsm executable

    """
    if len(args) == 1 and (args[0].lower() in ("-h", "-?", "--help")):
        args = ["*/*", "help"]
    # if no arguments are called
    if len(args) < 1:
        print("You must specify at least a server to work on", file=stderr)
        print(file=stderr)
        help(name, None, full_help=True)
        return 2

    # the first argument is either the server name, or the number of servers to run on
    servers = [args.pop(0)]
    # if the first letter in server is a number, we want to work with a number of servers
    if servers[0].isdigit():
        # how many servers?
        count = int(servers[0])
        # seperate them from the arguments
        servers = args[:count]
        args = args[count:]
        # we need at least 2 servers via this method
        if count < 1:
            print(
                "You must specify at least one server to work on",
                file=stderr
            )
            print(file=stderr)
            help(name, None)
            return 2
    # prevent servers having similar names to commnds
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

    # if no commands to run on the server(s)
    if len(args) < 1:
        print("You must specify at least a command to run", file=stderr)
        print(file=stderr)
        help(name, None, full_help=True)
        return 1

    # since we popped the servers from the args variable earlier,
    # we now get the command, and the arguments associated with the command
    # this command is what we operate on the server (e.g start, stop)
    cmd, *args = args
    cmd = cmd.lower()
    servers = [
        tuple(el if el != "all" else "*" for el in splitservername(spec))
        for spec in servers
    ]
    if len(servers) == 1 and servers[0] == ("*", "*") and cmd == "help":
        help(name, None, *args, file=stdout)
        return 0
    servers = [
        s for user, tag in servers for s in expandserverstar(user, tag, cmd)
    ]
    if len(servers) < 1:
        print("No servers found for", cmd, file=stderr)
        print(file=stderr)
        help(name, None)
        return 1
    elif len(servers) > 1:
        if cmd == "list":
            return runlistmulti(name, servers, [cmd] + args)
        else:
            return runmulti(name, len(servers), servers, [cmd] + args)
    else:  # count == 1
        return runone(name, servers[0], cmd, args)
    return 0


def runone(name, server, cmd, args):
    user, tag = server
    if user is not None:
        if cmd == "list":
            return runlistmulti(name, [server], [cmd] + args)
        else:
            return runas(name, user, tag, [cmd] + args)
    else:
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
                printhandledex(ex)
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
                printhandledex(ex)
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
                printhandledex(ex)
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
                printhandledex(ex)
                print(file=stderr)
                help(name, server, cmd)
                return 2
            # needed by activate and deactivate
            program.PATH = os.path.join(
                os.path.dirname(os.path.dirname(
                    os.path.realpath(os.path.abspath(__file__))
                )),
                "alphagsm"
            )
            try:
                server.run_command(cmd, *args, **opts)
                # developers: be sure to check if command_functions dictionary
                # has been filled, otherwise the error called here will make
                # no sense
            except ServerError as ex:
                print("Error running Command", file=stderr)
                printhandledex(ex)
                return 1
            except Exception as ex:
                print("Error running command", file=stderr)
                printhandledex(ex)
                return 3
    return 0


def splitservername(name):
    """
    This is used to select a server owned by a user
    """
    split = name.split("/")
    if len(split) == 1:
        # current user
        return None, split[0]
    elif len(split) == 2:
        # user and server
        return split[0], split[1]
    else:
        raise ServerError("Invalid server name. Only one / allowed")


def getallallservers(command):
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


def getalluserservers():
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


def expandserverstar(user, tag, cmd):
    if user == "*":
        if tag != "*":
            print("Error: Can't specify a server but '*' user")
            return ()
        else:
            return [splitservername(s) for s in getallallservers(cmd)]
    elif tag == "*" and user is None:
        return getalluserservers()
    else:
        return [(user, tag)]


def getrunascmd(name, user, server, args, multi=False):
    return ["sudo", "-Hu", user] + getruncmd(name, server, args, multi = multi)


def getruncmd(name, server, args, multi=False):
    scriptpath = os.path.join(
        os.path.dirname(os.path.dirname(
            os.path.realpath(os.path.abspath(__file__))
        )),
        "alphagsm-internal"
    )
    return [scriptpath, "1" if multi else "0", name, server] + args


def runas(name, user, server, args):
    ret = sp.call(getrunascmd(name, user, server, args))
    print("Command finished with return status", ret, file=stderr)
    return ret


def runlistmulti(name, servers, args):
    finalret = 0
    for user, server in servers:
        if user is not None:
            cmd = getrunascmd(name, user, server, args)
        else:
            cmd = getruncmd(name, server, args)
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


def _internalisrunning(line):
    return line.decode().strip() == "#%AlphaGSM-INTERNAL%#"


def runmulti(name, count, servers, args):
    multi = mp.Multiplexer()
    for user, server in servers:
        if user is not None:
            cmd = getrunascmd(name, user, server, args, True)
        else:
            cmd = getruncmd(name, server, args, True)
        mp.addtomultiafter(
            multi,
            (user + "/" if user is not None else "") + server,
            _internalisrunning,
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
