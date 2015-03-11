"""Documention for writing gamemodules.


A game server module is a python module in the gamemodules package somewhere
the python import mechanism can find it. It defines various attributes and
functions that provide the functionality for that particular game server.

The attributes and functions that can be specified in a gamemodule are
documented below grouped by the functionality they relate to. All functions and
attributes are required unless explicitly states.


Commands:
  This section documents the attributes related to providing commands for the
  server and modifying exisiting commands.
  Attributes:
    commands: the extra commands available for this type of server as a list.
        DO NOT include commands that the Server class provides but we modify.
    command_args: the arguments for any commands we provide and any extra
        optional arguments that we provide for built in commands in a
        dictionary with the command as the key. See the relevent command's
        section for how the extra arguments are passed though.
    command_descriptions: the descriptions for any commands we provide and any
        extra descriptions for built in commands in a dictionary with the 
        command as they key. The extra descriptions are appended to any default
        description.
    command_functions: the functions used to implement any commands we provide
        as a dictionary with the command as the key. Do not provide functions
        for built in commands here as they will be ignored. The functions are
        called by code of the form 
            module.command_functions[command](*args,**kwargs)
        where args and kwargs are the arguments and options defined in
        command_args.

Setup:
  This section documents the functions used by the setup built in command. Any
  extra arguments and options specified in command_args for "setup" are passed
  to the configure function.
  Functions:
    configure(server,ask,*args,**kwargs): Configure the server. If ask is true
      then prompt the user for input if not enough information is provided. If
      ask is false then throw a ServerError if required information is not
      provided or already in the data store. If the data store already has a
      key it should only be overwritten if instructed  by the user via either
      an argument or on a prompt. This function returns a tuple of args,kwargs
      to pass on to the install function.
   install(server,*args,**kwargs): Install the server. Once this returns the
      server should be ready to be started. This function should do any
      downloading or copying of files necessary for the server to run and setup
      any configururation files necessary for correct running.

Start:
  This section documents the functions used by the start built in command. All
  functions in this section receive the same set of extra arguments as defined
  in command_args. If Server class checks if the server is running before any
  of these functions are called.
  Functions:
    prestart(server,*args,**kwargs) [OPTIONAL]: Do anything that needs doing
      each time before the server start. Could include tidying logs, checking
      config is up to date, checking files are there, ...
    get_start_command(server,*args,**kwargs): Return the script and arguments
      to be called in the new screen session to start the server. The screen
      session will close when this command returns.
    poststart(server,*args,**kwargs) [OPTIONAL]: Do anything that needs doing
      each time after the server command is started. Could include sending
      initialisation commands to the server, checking it's actually running
      correctly, ...

Stop:
  This section documents the function and attribute used by the stop built in
  command. If this module can't stop the server before the timeout (see
  max_stop_wait) then tthe Server class will kill it by killing the screen
  session.
  Attributes:
    max_stop_wait [OPTIONAL]: The maximum number of minutes to wait for the
      server to stop. The timeout is capped at a maximum of 5 minutes
  Functions:
    do_stop(server,time,*args,**kwargs): Try and stop the server. This will
      be called repeatedly till the timeout is reached or the server is
      stopped. time is the number of minutes that have passed since we started
      trying to stop the server.
"""
