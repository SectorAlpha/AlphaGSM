import subprocess as sp
import os
import selectors

class ProcessReader(object):
  def __init__(self,tag,proc,stream,selector):
    self.tag=tag
    self.proc=proc
    self.selector=selector
    self.stream=stream
    self.selector.register(stream,selectors.EVENT_READ,self)
    self.data=b""
    print(tag,proc.pid,selectors.EVENT_READ)
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
    self.streamlessprocs=set()
  
  def run(self,tag,*args,**kwargs):
    return self.add(tag,sp.Popen(*args,**kwargs))
  
  def add(self,tag,proc):
    streams=[]
    if proc.stdout is not None:
      streams.append(ProcessReader(tag,proc,proc.stdout,self.selector))
    if proc.stderr is not None:
      streams.append(ProcessReader(tag,proc,proc.stderr,self.selector))
    self.streams+=len(streams)
    self.procs[proc]=streams
    if len(streams)==0:
      self.streamlessprocs.add((proc,tag))
    return proc

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
          self.selector.unregister(key.fileobj)
          key.fileobj.close()
          self.procs[key.data.proc].remove(key.data)
          self.streams-=1
          if len(self.procs[key.data.proc])==0:
            self.streamlessprocs.add((key.data.proc,key.data.tag))
      for proc,tag in self.streamlessprocs.copy():
        if proc.poll() is not None:
          del self.procs[proc]
          self.streamlessprocs.remove((proc,tag))
          print(tag,"has finished with status",proc.wait())
    else:
      pid,ret=os.waitpid(-1,0)
      for proc,tag in self.streamlessprocs.copy():
        if proc.poll() is not None:
          del self.procs[proc]
          self.streamlessprocs.remove((proc,tag))
          print(tag,"has finished with status",proc.wait())
    return self.streams

  def processall(self):
    while self.process() is not None: pass
      
       

