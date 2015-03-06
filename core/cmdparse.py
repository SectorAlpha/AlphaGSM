from itertools import chain


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
  while len(args)>0:
    arg=args.pop(0)
    if len(arg)>0 and arg[0]=="-":
      if len(arg)>1 and arg[1]=="-":
        if arg[2:] not in longopts:
          raise OptionException("Option '"+arg[2:]+"'not known")
        else:
          _,_,_,target,arg,value=opts[longopts[arg[2:]]]
          if arg is None:
            outopts[target]=value
          else:
            outopts[target]=value(args.pop(0))
      else:
        for c in arg[2:]:
          if c not in shortopts:
            raise OptionException("Option '"+c+"'not known")
          else:
            _,_,_,target,arg,value=opts[shortopts[arg[2]]]
            if arg is None:
              outopts[target]=value
            else:
              outopts[target]=value(args.pop(0))
    else:
      outargs.append(arg)
  if len(outargs)<len(reqargs):
    raise OptionException("Not enough arguments provided")
  if (catcharg is None or catcharg is False) and len(outargs)>len(reqargs)+len(optargs):
    raise OptionException("Too many arguments provided")
  return outargs,outopts

def shorthelp(cmd,defns):
  print(cmd,end="")
  if len(defns[3])>0:
    print(" [OPTION]...",end="")
  for arg,_,_ in defns[0]:
    print(" "+arg,end="")
  for arg,_,_ in defns[1]:
    print(" ["+arg+"]",end="")
  if defns[2] is True:
    print("...",end="")
  print()

def longhelp(cmd,cmddesc,defns):
  shorthelp(cmd,defns)
  print()
  if cmddesc is not None:
    print(cmddesc)
    print()
  reqargs,optargs,catcharg,opts=defns
  if len(reqargs)>0 or len(optargs)>0:
    print("Arguments:")
    for arg,desc,_ in reqargs:
      print("  "+arg+": "+desc)
    for arg,desc,_ in optargs:
      print("  "+arg+": "+desc)
    print()
  if len(opts)>0:
    print("Options:")
    for short,long,desc,_,arg,_ in opts:
      print("  ",end="")
      print(*chain(("-"+s for s in short),("--"+l for l in long)),sep=", ",end="")
      if arg is not None:
        print(" "+arg+" ",end="")
      print(": "+desc)
    print()

def serverhelp(server):
  for cmd in server.get_commands():
    shorthelp(cmd,server.get_command_args(cmd))

