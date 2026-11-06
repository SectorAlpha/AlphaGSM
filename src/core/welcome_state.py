"""Non-secret, per-operator acknowledgement of the optional first-run tour."""

import os
from pathlib import Path
import stat

from utils.settings import settings
from utils.state_io import sync_directory


def state_path():
    """Use the configured operator home, outside server and agent datastores."""
    home = settings.user.getsection('core').get('alphagsm_path', '~/.alphagsm')
    return Path(os.path.expanduser(home)) / 'welcome-v1.done'


def seen():
    """Recognize an ordinary owned marker without opening links or special files."""
    try:
        info = state_path().lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(info.st_mode) and (
        not hasattr(os, 'getuid') or info.st_uid == os.getuid())


def remember(choice):
    """Exclusively create a small acknowledgement; never replace an existing path."""
    path = state_path()
    if path.parent.is_symlink():
        raise OSError('Tour preference directory must not be a symlink')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.parent.stat()
    if hasattr(os, 'getuid') and info.st_uid != os.getuid():
        raise OSError('Tour preference directory must be owned by you')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        if not seen():
            raise OSError('Tour preference path is not an owned regular file') from None
        return
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        handle.write(choice + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    sync_directory(path.parent)
