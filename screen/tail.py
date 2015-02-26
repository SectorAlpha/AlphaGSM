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

def tail(filename, tailbytes = 0, sleepfor = 5):
    '''Examine file looking for new lines.
       When called, this function will process all lines in the file being
       tailed, detect the original file being renamed or reopened, etc... and
       sleep if nothing is found. If the file can't be opened raises StopIteration
       
       @return Nothing
       @param filename File to read.
       @param tailbytes Specifies bytes from end of file to start reading
         (defaults to 0, meaning skip entire file, -1 means read full file).
       @param sleepfor Amount of time to sleep between attempts to read
    '''
    fp = None
    lastSize = 0
    lastInode = -1
    data = ''
    while 1:
      #  open file if it's not already open
      if not fp:
        try:
          fp = open(filename, 'r')
          stat = os.stat(filename)
          lastIno = stat[1]
          if tailbytes >= 0 and stat[6] > tailbytes:
            fp.seek(0 - (tailbytes), 2)
          tailbytes = -1
          lastSize = 0
        except (IOError, OSError):
          if fp:
            fp.close()
          skip = -1    #  if the file doesn't exist, we don't skip
          fp = None
      if not fp:
        raise StopIteration()

      #  check to see if file has moved under us
      try:
        stat = os.stat(filename)
        thisSize = stat[6]
        thisIno = stat[1]
        if thisSize < lastSize or thisIno != lastIno:
          raise OSError(0,"file updated")
      except OSError:
        fp.close()
        fp = None
        data = ''
        continue

      #  read if size has changed
      if lastSize < thisSize:
        while 1:
          thisData = fp.read(4096)
          if len(thisData) < 1:
            break
          print "read data '"+thisData+"'"
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

      lastSize = thisSize
      lastIno = thisIno
      time.sleep(sleepfor)

__all__=["tail"]
