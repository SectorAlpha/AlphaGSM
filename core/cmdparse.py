from itertools import chain
import textwrap

class OptionError(Exception):
  pass

def parse(inargs,defns):
  reqargs,optargs,catcharg,opts=defns
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
  while len(inargs)>0:
    arg=inargs.pop(0)
    if len(arg)>0 and arg[0]=="-":
      if len(arg)>1 and arg[1]=="-":
        if arg[2:] not in longopts:
         raise OptionError("Option '"+arg[2:]+"'not known")
        else:
          _,_,_,target,arg,value=opts[longopts[arg[2:]]]
          if arg is None:
            outopts[target]=value
          else:
            if len(inargs)<1:
              raise OptionError("No argument for option '--"+arg[2:]+"'")
            try:
              outopts[target]=value(inargs.pop(0))
            except ValueError:
              raise OptionError("Argument isn't of the right format for option '--"+arg[2:]+"'")
      else:
        for c in arg[1:]:
          if c not in shortopts:
            raise OptionError("Option '"+c+"'not known")
          else:
            _,_,_,target,arg,value=opts[shortopts[c]]
            if arg is None:
              outopts[target]=value
            else:
              if len(inargs)<1:
                raise OptionError("No argument for option '-"+c+"'")
              try:
                outopts[target]=value(inargs.pop(0))
              except ValueError:
                raise OptionError("Argument isn't of the right format for option '-"+c+"'")
    else:
      outargs.append(arg)
  if len(outargs)<len(reqargs):
    raise OptionError("Not enough arguments provided")
  if (catcharg is None or catcharg is False) and len(outargs)>len(reqargs)+len(optargs):
    raise OptionError("Too many arguments provided")
  try:
    outargs=[value(arg) for arg,(_,_,value) in zip(outargs,_replast(reqargs+optargs))]
  except ValueError:
    raise OptionError("Argumant isn't of the right format")
  return outargs,outopts

def _replast(a):
  last=None
  for el in a:
    last=a
    yield a
  while True:
    yield a

def shorthelp(cmd,cmddesc,defns):
  s=cmd
  if len(defns[3])>0:
    s+=" [OPTION]..."
  for arg,_,_ in defns[0]:
    s+=" "+arg
  for arg,_,_ in defns[1]:
    s+=" ["+arg+"]"
  if defns[2] is True:
    s+="..."
  if cmddesc is not None:
    s+=" : "+cmddesc.splitlines()[0]
  print(textwrap.fill(s,80,initial_indent="  ",subsequent_indent="        "))

def longhelp(cmd,cmddesc,defns):
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


