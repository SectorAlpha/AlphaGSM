"""This module provides the data store used by servers."""
import os
import json
from collections.abc import MutableMapping

class DataError(Exception):
  """Thrown when there is an error reading or writing the data store"""
  pass

class JSONDataStore(MutableMapping):
  """Data store that uses json as it's storage engine"""
  def __init__(self,filename,_dict=None):
    """setup the data storeage backed by the file 'filename'.

    If the second optional argument is None or missing then load
    from the file else just used the provided data store.
    """
    self.filename=filename
    if _dict is None:
      self._dict={}
      self.load()
    else:
      self._dict=_dict

  def __len__(self):
    """Get the number of items in the data store"""
    return len(self._dict)
  def __getitem__(self,key):
    """Get the item called 'key'."""
    return self._dict[key]
  def get(self,key,default=None):
    """Get the item called 'key'."""
    return self._dict.get(key,default)
  def __setitem__(self,key,value):
    """Set the item called 'key' to 'value'."""
    self._dict[key]=value
  def __delitem__(self,key):
    """Delete the item called 'key' from this data store."""
    del self._dict[key]
  def __iter__(self):
    """Iterator over the keys in this data store."""
    return iter(self._dict)
  def __contains__(self,item):
    """Check if 'item' is valid key for this data store."""
    return item in self._dict
  def setdefault(self,key,default):
    """If 'key' is not in this data store then set it to 'default'. Return the current value."""
    return self._dict.setdefault(key,default)
  def load(self):
    """Load the data from the data store's file. Completely replaces any current data."""
    if not os.path.isfile(self.filename):
      raise DataError("file doesn't exist: "+self.filename)
    with open(self.filename, 'r') as fp:
      data = json.load(fp)
    self._dict=data
  def save(self):
    """Save the data to the data store's file."""
    with open(self.filename, 'w') as fp:
      json.dump(self._dict,fp)
  def prettydump(self):
    """A pretty formated string version of the data for showing to users."""
    return json.dumps(self._dict,indent=2,separators=(",",": "),sort_keys=True)
    
    
__all__=["DataError","JSONDataStore"]    

