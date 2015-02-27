import os
import json

class JSONDataStore(object):
  def __init__(self,filename):
    self.filename=filename
    self._dict={}
    self.load()

  def __getitem__(self,key):
    return self._dict[key]
  def __setitem__(self,key,value):
    self._dict[key]=value
  def __delitem__(self,key)
    del self._dict[key]
  def __iter__(self):
    return iter(self._dict)
  def __contains__(self,item):
    return item in self._dict
  def setdefault(self,key,default):
    return self._dict.setdefault(key,default)
  def load(self):
    if os.path.isfile(self.filename):
      with open(self.filename, 'rb') as fp:
        data = json.load(fp)
      self._dict=data
  def save(self):
    with open(self.filename, 'wb') as fp:
      json.sump(fp,self._dict)
    
    
    

