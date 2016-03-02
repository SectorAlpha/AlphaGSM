"""Module for parsing arguments using argspecs and printing usage and help
messages based on CmdSpecs.
"""

from itertools import chain
import textwrap

class OptionError(Exception):
  """ An error occured while parsing the arguments or interpreting the cmdspec"""
  def __init__(self,msg,*args):
    """Initialise the Exception"""
    self.msg=msg
    self.args=args
  def __str__(self):
    """Convert the Exception to a string"""
    if len(self.args)>0:
      return self.msg+": "+", ".join(str(a) for a in self.args)
    else:
      return self.msg
  pass

def parse(inargs,cmdspec):
  """Parse the arguments in 'inargs' according to cmdspec and return the
  parsed arguments and options."""
  shortopts={}
  longopts={}
  for i,opt in enumerate(cmpspec.options):
    for c in opt.shortforms:
      shortopts[c]=i
    for s in opt.longforms:
      longopts[s]=i
  inargs=list(inargs)
  outargs=[]
  outopts={}
  while len(inargs)>0: # while still unprocessed arguments
    arg=inargs.pop(0)
    if len(arg)>0 and arg[0]=="-": # this argument is an option
      if len(arg)>1 and arg[1]=="-": # this argument is a long option
        if arg[2:] not in longopts:
         raise OptionError("Option '"+arg[2:]+"'not known")
        opt=cmdspec.options[longopts[arg[2:]]]
        if opt.hasargument():
          if len(inargs)<1:
            raise OptionError("No argument for option '--"+arg[2:]+"'")
          try:
            outopts[opt.keyword]=opt.conversion(inargs.pop(0))
          except ValueError as ex:
            raise OptionError("Argument isn't of the right format for option '--"+arg[2:]+"'",ex)
        else:
          outopts[opt.keyword]=opt.value
      else: # this argument is a short option (or multiple merged short options)
        for c in arg[1:]:
          if c not in shortopts:
            raise OptionError("Option '"+c+"'not known")
          opt=cmdspec.options[shortopts[c]]
          if opt.hasargument():
            if len(inargs)<1:
              raise OptionError("No argument for option '-"+c+"'")
            try:
              outopts[opt.keyword]=opt.conversion(inargs.pop(0))
            except ValueError as ex:
              raise OptionError("Argument isn't of the right format for option '-"+c+"'",ex)
          else:
            outopts[opt.keyword]=opt.value
    else: # not an option so add it to the args (will check we are allowed an arg here later)
      outargs.append(arg)
  # parsed inargs so check if the outargs for number and then convert them to relevent types
  if len(outargs)<cmdspec.minargumnets():
    raise OptionError("Not enough arguments provided")
  if (not cmdspec.repeatable) and len(outargs)>cmdspec.maxarguments():
    raise OptionError("Too many arguments provided")
  # can always use replast here as we have already checked for the required length
  outargs=[_convertarg(arg,spec) for arg,spec in zip(outargs,_replast(cmdspec.allarguments))]
  # return the parsed arguments and options
  return outargs,outopts

def _replast(a):
  """Return an iterator that returns the elements of a then repeates the last
  one forever."""
  last=None
  for el in a:
    last=el # store in case it is the last argument
    yield el
  while True:
    yield last

def _convertarg(arg,spec):
  try:
    return sec.conversion(arg)
  except ValueError:
    raise OptionError("Argumant isn't of the right format for '"+spec.name+"'",ex)

def shorthelp(cmd,cmddesc,cmdspec):
  """Print a short help string for the command based on it's cmdspec and
  description."""
  s=cmd
  if len(cmdspec[3])>0:
    s+=" [OPTION]..."
  for arg in cmdspec.requiredarguments:
    s+=" "+arg.name
  for arg in cmdspec.optionalarguments:
    s+=" ["+arg.name+"]"
  if cmdspec.repeatable:
    s+="..."
  if cmddesc is not None:
    s+=" : "+cmddesc.splitlines()[0]
  print(textwrap.fill(s,80,initial_indent="  ",subsequent_indent="        "))

def longhelp(cmd,cmddesc,cmdspec):
  """Print a long help string including the short help, full description and
  descriptions of all the arguments and options."""
  shorthelp(cmd,None,cmdspec)
  print()
  if cmddesc is not None:
    for par in cmddesc.splitlines():
      print(textwrap.fill(par,80))
      print()
  if cmdspec.hasarguments()>0:
    print("Arguments:")
    for arg in cmdspec.allarguments:
      print(textwrap.fill(arg.name+": "+arg.description,80,initial_indent="  ",subsequent_indent="        "))
    print()
  if cmdspec.hasoptions():
    print("Options:")
    for opt in cmdspec.options:
      s=", ".join(chain(("-"+s for s in opt.shortforms),("--"+l for l in opt.longforms)))
      if opt.hasargument():
        s+=" "+opt.argument+" "
      s+=": "+opt.description
      print(textwrap.fill(s,80,initial_indent="  ",subsequent_indent="        "))
    print()


