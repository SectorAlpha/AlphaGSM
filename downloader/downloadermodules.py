"""Documentation for downloadermodules

Downloadermodules are python modules in the downloadermodules package somewhere
the python import mechanism can find it. It defines various functions that provide
the functionality for that particular type of download.

The two required functions are download and getfilter.

download(path,args): this function is called to actually perform a download.
    The download must be stored in the directory path. If the download can't
    be performed then this function should raise a DownloadError exception.
    Interpretation of the args is entirely up to the module to decide but will
    always be provided as a list of strings.

getfilter(sort=None,**kwargs): this function is called to get filter and sort
    key functions. The 'sort' argument specifies the sort order. Valid values is
    up to the module except for None in which case the short function returned
    should be the literal None to signify don't sort. The other keyword arguments
    are up to the module both in terms of valid keys and their valid values and are
    used to define the filter to use. This function then needs to return a pair
    of functions, the first being the filter function and the second being either
    a function to return the sort key or None if unsorted output is requested.
    Both functions will be called with arguments being the elements of an entry in
    the list returned by download.downloader.getpaths
"""
