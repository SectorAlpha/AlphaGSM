"""Module to download game servers and cache and share the downloads"""

from importlib import import_module
import contextlib
import getpass
import os
import time
import random
import sys
from urllib.parse import quote, unquote
from utils.platform_info import IS_WINDOWS
from utils.settings import settings

if not IS_WINDOWS:
    import pwd  # pylint: disable=import-error
else:
    pwd = None  # pylint: disable=invalid-name


def expandcustomuser(path, user):
    """Expand a `~/` path using the home directory of the named user."""
    if path[0:2] == "~/":
        if IS_WINDOWS or user is None:
            return os.path.expanduser("~") + path[1:]
        return pwd.getpwnam(user).pw_dir + path[1:]
    return path


def current_user():
    """Return the current POSIX account name, if the runtime UID has one."""
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        # Docker can deliberately run with a host UID that is not in /etc/passwd.
        return None


# NONE OF THESE PATHS SHOULD BE ON A NFS!
# If they are there may be race conditions and database corruption


RAW_USER = settings.system.getsection("downloader").get("user")
USER_SET = RAW_USER != None
if USER_SET:
    USER = RAW_USER
elif IS_WINDOWS:
    USER = getpass.getuser()
else:
    USER = current_user()
DB_PATH = expandcustomuser(
    settings.get(USER_SET).getsection("downloader").get("db_path")
    or os.path.join(
        settings.get(USER_SET).getsection("core").get("alphagsm_path", "~/.alphagsm"),
        "downloads/downloads.txt",
    ),
    USER,
)
TARGET_PATH = expandcustomuser(
    settings.system.getsection("downloader").get("target_path")
    or os.path.join(
        settings.get(USER_SET).getsection("core").get("alphagsm_path", "~/.alphagsm"),
        "downloads/downloads",
    ),
    USER,
)

DOWNLOADERS_PACKAGE = settings.system.getsection("downloader").get(
    "downloaders_package", "downloadermodules."
)
UPDATE_SUFFIX = ".new"
LOCK_SUFFIX = ".lock"

LOCK_PATH = DB_PATH + LOCK_SUFFIX
UPDATE_PATH = DB_PATH + UPDATE_SUFFIX

PARENTLEN = settings.user.getsection("downloader").getsection("pathgen").get("parentlen", 1)
PARENTCHARS = settings.user.getsection("downloader").getsection("pathgen").get(
    "parentchars", "abcdefghijklmnopqrstuvxyz"
)

DIRLEN = settings.user.getsection("downloader").getsection("pathgen").get("dirlen", 8)
DIRCHARS = settings.user.getsection("downloader").getsection("pathgen").get(
    "dirchars", "abcdefghijklmnopqrstuvwxyz0123456789_"
)

MAX_TRIES = settings.user.getsection("downloader").getsection("pathgen").get("maxtries", 238328)
RETRYPARENT = MAX_TRIES // 10

__all__ = [
    "DownloaderError",
    "getpath",
    "getpathifexists",
    "main",
    "getpaths",
    "getargsforpath",
    "run_download_helper",
]


class DownloaderError(Exception):
    """An error thrown when attempting to perform a download"""

    def __init__(self, msg, *args, ret=1, **kwargs):
        """Store a downloader-specific return code alongside the error message."""
        super(DownloaderError, self).__init__(msg, *args, **kwargs)
        self.ret = ret


def _findmodule(name):
    """Resolve a downloader module name, following namespace and alias indirection."""
    name = str(name)
    if len(name) < 2 or not all((len(el) > 0 and el.isalnum()) for el in name.split(".")):
        raise DownloaderError("Invalid module requested: " + name)
    try:
        module = import_module(DOWNLOADERS_PACKAGE + name)
    except ImportError as ex:
        # If the requested name is a package namespace, try its DEFAULT submodule
        try:
            module = import_module(DOWNLOADERS_PACKAGE + name + ".DEFAULT")
        except ImportError:
            raise DownloaderError("Can't find module: " + name, ex)
    # Return the resolved module directly; do not follow ALIAS_TARGET legacy indirection.
    return module


def generatepath():
    """Generate a new (not previously existing) path within TARGET_PATH. Returns None if no path can be generated"""
    # check if the target directory exists
    if not os.path.exists(TARGET_PATH):
        try:
            os.makedirs(TARGET_PATH)
        except FileExistsError:
            pass
    rnd = random.Random()
    # choose a destination path
    for seq in range(MAX_TRIES):
        if seq % RETRYPARENT == 0:
            dirn = os.path.join(
                TARGET_PATH, "".join(rnd.choice(PARENTCHARS) for i in range(PARENTLEN))
            )
            if not os.path.isdir(dirn):
                try:
                    os.mkdir(dirn, 0o755)
                except FileExistsError:
                    pass

        path = os.path.join(dirn, "".join(rnd.choice(DIRCHARS) for i in range(DIRLEN)))
        try:
            os.mkdir(path, 0o755)
            return path
        except FileExistsError:
            continue  # try again
    return None


# This will always run while the DB is locked
def download(module, args):
    """Actually do a download.

    Returns the path that the download was downloaded to.
    This function locates and imports the module requested then delegates to that for the actual download.
    Should only by run while the DB lock is help.
    """
    path = generatepath()
    if path is None:
        raise DownloaderError(
            "Can't generate storage path. Clear out unused paths from the database"
        )
    mod = _findmodule(module)
    mod.download(path, args)
    return path


def getpathifexists(module, args):
    """Check if a path for the download is already in the database and if so return it else return None"""
    sargs = ",".join(quote(a) for a in args)
    # check if DB_PATH exists, if not make it
    if not os.path.exists(DB_PATH):
        make_dirs = DB_PATH.rsplit("/", 1)[0]
        try:
            os.makedirs(make_dirs)
        except FileExistsError:
            pass
        open(DB_PATH, "a").close()
        return None
    with open(DB_PATH, "r") as f:
        for line in f:
            lmodule, largs, llocation, ldate, lactive = line.split()
            if int(lactive) and lmodule == module and largs == sargs:
                return llocation
    return None


def getpath(module, args):
    """Get the path for a download, downloading it if it isn't already downloaded.

    Can be run as any user and will change user to the download systems owner if it needs downloading
    """
    path = getpathifexists(module, args)
    if path is not None:
        return path

    if not IS_WINDOWS and USER is not None and os.getuid() != pwd.getpwnam(USER).pw_uid:
        import subprocess as sp

        if getattr(sys, "frozen", False):
            launcher = [sys.executable, "--_download"]
        else:
            launcher = [os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(os.path.abspath(__file__))))),
                "alphagsm-downloads",
            )]
        try:
            path = sp.check_output(["sudo", "-Hu", str(USER)] + launcher + [module] + list(args))
        except sp.CalledProcessError as ex:
            raise DownloaderError("Error downloading file", ret=ex.returncode)
        else:
            return unquote(path.decode("ascii").strip())

    # Definitely running as correct user now and file not found (yet) but may have other threads updating the file so lock then check again

    while True:
        try:
            open(LOCK_PATH, "x")
        except FileExistsError:
            time.sleep(1)
            continue
        else:
            break
    try:
        # Now locked so no-one else can be changing it
        path = getpathifexists(module, args)
        if path is not None:
            return path

        # definitely doesn't exist so we need to download it
        path = download(module, args)

        sargs = ",".join(quote(a) for a in args)

        try:
            os.remove(UPDATE_PATH)
        except FileNotFoundError:
            pass
        with open(UPDATE_PATH, "w") as f:
            with open(DB_PATH, "r") as f2:
                for l in f2:
                    f.write(l)
            f.write(" ".join((module, sargs, path, str(time.time()), str(1))) + "\n")
        os.rename(UPDATE_PATH, DB_PATH)
        return path
    finally:
        os.remove(LOCK_PATH)


def run_download_helper(args):
    """Serve the standalone equivalent of alphagsm-downloads' quoted-path CLI."""
    if not args:
        print("A download module is required.", file=sys.stderr)
        return 2
    with contextlib.redirect_stdout(sys.stderr):
        try:
            path = getpath(args[0], args[1:])
        except DownloaderError as ex:
            print(ex)
            return ex.ret
    print(quote(path))
    return 0


main = getpath


def _true(*arg):
    """Return true for every record, for use as a default filter predicate."""
    return True


def _getallfilter(active=None, sort=None):
    """a default filter that applies to any download module"""
    filterfn = _true
    sortfn = None
    if active != None:
        active = bool(active)
        filterfn = lambda lmodule, largs, llocation, ldate, lactive: active == bool(int(lactive))
    if sort == "date":
        sortfn = lambda lmodule, largs, llocation, ldate, lactive: float(ldate)
    elif sort is not None:
        raise DownloaderError("Unknown sort key")
    return filterfn, sortfn


def getpaths(module, sort=None, **filter):
    """get all paths for the given module that match a specified filter, optionally sorted.

    The complete list of filters available is module dependant. If module is None then the
    only valid filter is active=True/False/None which filters on the active state and the only
    valid sort order is 'date'. The module's filter function is called 'getfilter' and should
    document the valid filters and sort orders.

    The result is a list of tuples that contains the elements:
            (module_name,[list,of,arguments],path,date_added,is_active)
    """
    if module is None:
        filterfn, sortfn = _getallfilter(sort=sort, **filter)
    else:
        filterfn, sortfn = _findmodule(module).getfilter(sort=sort, **filter)
    downloads = []
    with open(DB_PATH, "r") as f:
        for line in f:
            lmodule, largs, llocation, ldate, lactive = line.split()
            largs = [unquote(arg) for arg in largs.split(",")]
            if (module is None or lmodule == module) and filterfn(
                lmodule, largs, llocation, ldate, lactive
            ):
                downloads.append((lmodule, largs, llocation, ldate, lactive))
    if sortfn:
        downloads.sort(key=lambda record: sortfn(*record))
    return downloads


def getargsforpath(path):
    """Get the module and arguments for a download path or return None if not a valid path"""
    with open(DB_PATH, "r") as f:
        for line in f:
            lmodule, largs, llocation, ldate, lactive = line.split()
            if llocation == path:
                return (lmodule, [unquote(arg) for arg in largs.split(",")])
    return None
