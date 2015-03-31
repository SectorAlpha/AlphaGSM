from importlib import import_module

# This will always run while a read lock is held on the db
# and a write lock on the db update file
def download(module,args):
  # choose a destination path
  # find a previous version's path
  mod=import_module(module)
  mod.download(path,args,previous=previouspath)
  return path

def main(args):
  #do stuff
  return 1
