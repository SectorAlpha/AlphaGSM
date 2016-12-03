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
        pass
    else:  # Something unexpected went wrong so reraise the exception.
        raise
  else:  # No exception, so the file must have been created successfully.
    # Using `os.fdopen` converts the handle to an object that acts like a
    # regular Python file object, and the `with` context manager means the
    # file will be automatically closed when we're done with it.
    os.fdopen(file_handle, 'w')

