import subprocess as sp
import os
import selectors

class ProcessReader(object):
  def __init__(self,tag,proc,stream):
    self.tag=tag
    self.proc=proc
    self.stream=stream
    self.data=b""
  def read(self):
    new=self.stream.read1(1000)
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
    self.procs={}
    self.streams=0
    self.streamlessprocs={}
  
  def run(self,tag,*args,**kwargs):
    return self.addproc(tag,sp.Popen(*args,**kwargs))
  
  def addproc(self,tag,proc):
    if proc.stdout is not None:
      self.addstream(proc,ProcessReader(tag,proc,proc.stdout))
    if proc.stderr is not None:
      self.addstream(tag,proc,ProcessReader(tag,proc,proc.stderr))
    self.addbareproc(tag,proc)
    return proc

  def addbareproc(self,tag,proc):
    if proc not in self.procs:
      self.procs[proc]=[]
    if len(self.procs[proc])==0:
      self.streamlessprocs[proc]=tag

  def addstream(self,proc,reader):
    self.selector.register(reader.stream,selectors.EVENT_READ,reader)
    if proc not in self.procs:
      self.procs[proc]=[]
    elif proc in self.streamlessprocs:
      del self.streamlessprocs[proc]
    self.procs[proc].append(reader)
    self.streams+=1

  def removestream(self,proc,reader):
    self.selector.unregister(reader.stream)
    self.procs[proc].remove(reader)
    self.streams-=1
    if len(self.procs[proc])==0:
      self.streamlessprocs[proc]=reader.tag

  def removeproc(self,proc):
    for stream in self.procs[proc]:
      self.removestream(proc,stream)
    del self.procs[proc]
    del self.streamlessprocs

  def transfer(self,target,proc):
    for stream in self.procs[proc]:
      self.removestream(proc,stream)
      target.addstream(proc,stream)
    #all streams removed so now should be in streamlessprocs
    target.addbareproc(self.streamlessprocs[proc],proc)
    del self.streamlessprocs[proc]
    del self.procs[proc]

  def process(self,timeout=None):
    print("PROCESS")
    if len(self.procs)<1:
      return None
    if self.streams>0:
      inputs=self.selector.select(timeout)
      for key,events in inputs:
        hasread=key.data.read()
        for l in key.data.consumelines():
          print(key.data.tag+": ",l.decode())
        if not hasread:
          if len(key.data.data)>0:
            print(key.data.tag+": ",key.data.data.decode())
          self.removestream(key.data.proc,key.data)
          key.fileobj.close()
      for proc,tag in list(self.streamlessprocs.items()):
        if proc.poll() is not None:
          del self.procs[proc]
          del self.streamlessprocs[proc]
          print(tag,"has finished with status",proc.wait())
    else:
      pid,ret=os.waitpid(-1,0)
      for proc,tag in list(self.streamlessprocs.items()):
        if proc.poll() is not None:
          del self.procs[proc]
          del self.streamlessprocs[proc]
          print(tag,"has finished with status",proc.wait())
    return self.streams


  def processall(self):
    while self.process() is not None: pass
      
       

