import os
import errno

def make_empty_file(file_path):
  """
  check_exists: if the file exists, then do not make the empty file
  """

  flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY

  try:
    file_handle = os.open(file_path, flags)
  except OSError as e:
    if e.errno == errno.EEXIST:  # Failed as the file already exists.
        os.close(file_handle)
        pass
    else:  # Something unexpected went wrong so reraise the exception.
        raise OSError
  else:  # No exception, so the file must have been created successfully.
    os.fdopen(file_handle, 'w')
    os.close(file_handle)
    

