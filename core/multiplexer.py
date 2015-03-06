import subprocess as sp
import selectors

class Process(object):
  def __init__(self,tag,proc,selector):
    self.tag=tag
    self.proc=proc
    self.selector=selector
    self.selector.register(proc.stdout,selectors.EVENT_READ,self)
    self.data=b""
    print(tag,proc.pid,selectors.EVENT_READ)
  def read(self):
    new=self.proc.stdout.read1(1000)
    self.data+=new
    return len(new)>0
  def consumelines(self):
    while True:
      i=self.data.find(b"\n")
      if i<0:
        return
      tmp=self.data[:i]
      self.data=self.data[i+1:]
      yield tmp

class Multiplexer(object):
  def __init__(self):
    self.selector=selectors.DefaultSelector()
    self.procs=[]
  
  def run(self,tag,*args,**kwargs):
    self.procs.append(Process(tag,sp.Popen(*args,stdout=sp.PIPE,stderr=sp.STDOUT,stdin=sp.DEVNULL,**kwargs),self.selector))
  
  def process(self,timeout=None):
    if len(self.procs)<1:
      return None
    inputs=self.selector.select(timeout)
    for key,events in inputs:
      hasread=key.data.read()
      for l in key.data.consumelines():
        print(key.data.tag+": ",l.decode())
      if not hasread and key.data.proc.poll()!=None:
        if len(key.data.data)>0:
          print(key.data.tag+": ",key.data.data.decode())
        self.selector.unregister(key.fileobj)
        key.fileobj.close()
        self.procs.remove(key.data)
        print(key.data.tag,"has finished with status",key.data.proc.wait())
    return len(inputs)

  def processall(self):
    while self.process() is not None: pass
      
       

