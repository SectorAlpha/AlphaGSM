"""Documention for writing gamemodules.


A game server module is a python module in the gamemodules package somewhere
the python import mechanism can find it. It defines various attributes and
functions that provide the functionality for that particular game server.

The attributes and functions that can be specified in a gamemodule are
documented below grouped by the functionality they relate to.


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
        for built in commands here as they will be ignored.

Setup:
  This section documents the commands used by the setup built in command. Any
  extra options specified in command_args for "setup" are passed to the
  configure function.
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


      
"""
