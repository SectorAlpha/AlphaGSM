'''A module which implements a unix-like "tail" of a file.
A callback is made for every new line found in the file.  Options
specify whether the existing contents of the file should be read
or ignored.

If a file is emptied or removed, the tail will continue reading lines
which are written in the new place.

  for line in tail(filename):
    <process line>
    if <stop condition>:
      break;
  else:
    <no such file code>
'''

import time
import string
import os


def tail(filename, tailbytes = 0, sleepfor = 2, timeout=-1):
  '''Examine file looking for new lines.
     When called, this function will process all lines in the file being
     tailed, detect the original file being renamed or reopened, etc... and
     sleep if nothing is found. If the file can't be opened raises StopIteration
     
     @return Nothing
     @param filename File to read.
     @param tailbytes Specifies bytes from end of file to start reading
       (defaults to 0, meaning skip entire file, -1 means read full file).
     @param sleepfor Amount of time to sleep between attempts to read
     @param timeout Amount of time to yield after even if no new input. If the 
       timeout triggers then we yield None
  '''
  try:
    fp = open(filename, 'r')
    stat = os.stat(filename)
    lastInode = stat[1]
    if tailbytes >= 0 and stat[6] > tailbytes:
      fp.seek(0 - (tailbytes), 2)
    return _gen(filename,fp,lastInode,sleepfor,timeout)
  except (IOError, OSError):
    if fp:
      fp.close()
    return _gen(filename,None,-1,sleepfor)

def _nogen():
  return
  yield
def _gen(filename, fp, lastInode, sleepfor,timeout):
    lastSize = 0
    data = ''
    sleeps=0 # sleeps since last succesful yield
    while 1:
      #  open file if it's not already open
      if not fp:
        try:
          fp = open(filename, 'r')
          stat = os.stat(filename)
          lastInode = stat[1]
        except (IOError, OSError):
          if fp:
            fp.close()
          fp = None
      if not fp:
        raise StopIteration()

      #  read any new data
      while 1:
        thisData = fp.read(4096)
        if len(thisData) < 1:
          break
        print(("read data '"+thisData+"'"))
        data = data + thisData
        #  process lines within the data
        while 1:
          pos = string.find(data, '\n')
          if pos < 0:
            break
          line = data[:pos]
          data = data[pos + 1:]
          #  line is line read from file
          yield line
          sleeps=1
      #  check to see if file has moved under us
      try:
        stat = os.stat(filename)
        thisSize = stat[6]
        thisInode = stat[1]
        if thisSize < lastSize or thisInode != lastInode:
          raise OSError(0,"file updated")
      except OSError:
        yield data # give rest of data as a line even if no newline if we are starting a new input file (implict \n at start of new file)
        fp.close()
        fp = None
        data = ''
        continue
      lastSize = thisSize
      lastInode = thisInode
      if timeout>0 and sleeps*sleepfor>timeout:
        yield None
        sleeps=0
      else:
        time.sleep(sleepfor)
        sleeps+=1

__all__=["tail"]
