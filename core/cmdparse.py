"""Module for parsing arguments using argspecs and printing usage and help
messages based on cmdspecs.

Cmdspecs are a tuple of 4 elements in the form
    (reqargs,optargs,repeatable,options)
where reqargs is the required arguments, optargs is the optional arguments,
repeatable says the last argument can be repeated as many times as wanted and
options describes the options available.

Both reqargs and optargs are a list of argument tuples each of which describes
an arguments. These argument tuples take the form
    (name,description,conversion)
where name is the name to display for the argument in help text (should be all
caps), description is the help message to describe the argument and conversion
is a function used to convert the input string to a valid format that should
raise ValueError if the input isn't valid.

Options is a list of option tuples each of which describes an option. These
option tuples take the form
    (shortforms,longforms,description,keyword,argument,value/conversion)
where shortforms is a string who's characters are used for the short form
options (i.e. -o), longorms is a list of the long forms for this option
(i.e. --option), description is the help message to descript the option,
keyword is the keyword to attach the value to if the option is present,
argument is either None if the option doesn't take a value or the name of the
argument for printing in help text (should be all caps) and value/conversion is
if argument is None the value to store with keyword, else the function used to
convert the option's argument to a form for storing (see conversion member of
argument tuples for more details).
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
  reqargs,optargs,catcharg,opts=cmdspec
  shortopts={}
  longopts={}
  for i,(sopt,lopt,_,_,_,_) in enumerate(opts):
    for c in sopt:
      shortopts[c]=i
    for s in lopt:
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
        else:
          _,_,_,target,arg,value=opts[longopts[arg[2:]]]
          if arg is None: # no argument
            outopts[target]=value
          else: #has an argument
            if len(inargs)<1:
              raise OptionError("No argument for option '--"+arg[2:]+"'")
            try:
              outopts[target]=value(inargs.pop(0))
            except ValueError:
              raise OptionError("Argument isn't of the right format for option '--"+arg[2:]+"'")
      else: # this argument is a short option (or multiple merged short options)
        for c in arg[1:]:
          if c not in shortopts:
            raise OptionError("Option '"+c+"'not known")
          else:
            _,_,_,target,arg,value=opts[shortopts[c]]
            if arg is None: # no argument
              outopts[target]=value
            else: # has an argument
              if len(inargs)<1:
                raise OptionError("No argument for option '-"+c+"'")
              try:
                outopts[target]=value(inargs.pop(0))
              except ValueError:
                raise OptionError("Argument isn't of the right format for option '-"+c+"'")
    else: # not an option so add it to the args (will check we are allowed an arg here later)
      outargs.append(arg)
  # parsed inargs so check if the outargs for number and then convert them to relevent types
  if len(outargs)<len(reqargs):
    raise OptionError("Not enough arguments provided")
  if (catcharg is None or catcharg is False) and len(outargs)>len(reqargs)+len(optargs):
    raise OptionError("Too many arguments provided")
  try:
    outargs=[value(arg) for arg,(_,_,value) in zip(outargs,_replast(reqargs+optargs))]
  except ValueError as ex:
    raise OptionError("Argumant isn't of the right format",ex)
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

def shorthelp(cmd,cmddesc,cmdspec):
  """Print a short help string for the command based on it's cmdspec and
  description."""
  s=cmd
  if len(cmdspec[3])>0:
    s+=" [OPTION]..."
  for arg,_,_ in cmdspec[0]:
    s+=" "+arg
  for arg,_,_ in cmdspec[1]:
    s+=" ["+arg+"]"
  if cmdspec[2] is True:
    s+="..."
  if cmddesc is not None:
    s+=" : "+cmddesc.splitlines()[0]
  print(textwrap.fill(s,80,initial_indent="  ",subsequent_indent="        "))

def longhelp(cmd,cmddesc,defns):
  """Print a long help string including the short help, full description and
  descriptions of all the arguments and options."""
  shorthelp(cmd,None,defns)
  print()
  if cmddesc is not None:
    for par in cmddesc.splitlines():
      print(textwrap.fill(par,80))
      print()
  reqargs,optargs,catcharg,opts=defns
  if len(reqargs)>0 or len(optargs)>0:
    print("Arguments:")
    for arg,desc,_ in reqargs:
      print(textwrap.fill(arg+": "+desc,80,initial_indent="  ",subsequent_indent="        "))
    for arg,desc,_ in optargs:
      print(textwrap.fill(arg+": "+desc,80,initial_indent="  ",subsequent_indent="        "))
    print()
  if len(opts)>0:
    print("Options:")
    for short,long,desc,_,arg,_ in opts:
      s=", ".join(chain(("-"+s for s in short),("--"+l for l in long)))
      if arg is not None:
        s+=" "+arg+" "
      s+=": "+desc
      print(textwrap.fill(s,80,initial_indent="  ",subsequent_indent="        "))
    print()


