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
        # If the file already exists, then this is not a problem
        # Otherwise something unexpected went wrong, so reraise the previous exception
        if e.errno != errno.EEXIST: raise  
        # The file was never opened since os.open threw an exception
    else:  
        # No exception, so the file must have been created successfully.
        # Finally, close the file.
        os.close(file_handle)
        

