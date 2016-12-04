import os
import errno

def make_empty_file(file_path):
  """
  Creates an empty file if the file does not exist.
  If the file exists, then an error is raised.
  """

  flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

  try:
    file_handle = os.open(file_path, flags)
  except OSError as e:
    if e.errno == errno.EEXIST:  # Failed as the file already exists.
        # no need to close the file handle
        # It is not opened due to errno.EEXIST being true
        pass
    else:  
        # Something unexpected went wrong so reraise the previous exception.
        raise
  else:  
    # No exception, so the file must have been created successfully.
    # Finally, close the file.
    os.close(file_handle)
    

