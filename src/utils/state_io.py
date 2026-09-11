"""Durable atomic writes and reentrant process locks for local state files.

Locks use a persistent sidecar inode: never delete a lock file while AlphaGSM
might be running. The operating system releases ownership after a process exits,
including abnormal exits. Callers must lock before loading state and keep the
lock through mutation and saving; locking only a write cannot prevent lost data.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
import errno
import os
from pathlib import Path
import stat
import tempfile
import threading
import time


@dataclass
class _LockState:
    mutex: object = field(default_factory=threading.RLock)
    depth: int = 0
    descriptor: object = None


_LOCKS = {}
_REGISTRY_MUTEX = threading.Lock()


def sync_directory(directory):
    """Persist directory entry changes where directory fsync is supported."""

    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        try:
            os.fsync(descriptor)
        except OSError as ex:
            if ex.errno not in (errno.EINVAL, errno.ENOTSUP, errno.EBADF):
                raise
    finally:
        os.close(descriptor)


def atomic_write_text(filename, content, *, mode=None, encoding="utf-8"):
    """Flush a same-directory temporary file before replacing its destination."""

    target = Path(filename).resolve()
    if mode is None:
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(prefix="." + target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding=encoding) as handle:
            os.chmod(temporary, mode)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        sync_directory(target.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _try_lock(descriptor):
    """Try to acquire a platform lock without blocking."""

    if os.name == "nt":
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(descriptor):
    """Release a platform lock before closing its descriptor."""

    if os.name == "nt":
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _acquire_process_lock(path, deadline):
    """Open a persistent sidecar and wait at most until the requested deadline."""

    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.fstat(descriptor).st_size == 0:
            os.write(descriptor, b"\0")
        while True:
            try:
                _try_lock(descriptor)
                return descriptor
            except OSError as ex:
                if ex.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("Server state is busy: %s; retry after the current command finishes." % path) from ex
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    except BaseException:
        os.close(descriptor)
        raise


@contextmanager
def state_lock(filename, *, timeout=30.0):
    """Lock state across load/mutate/save, allowing nested calls in this thread."""

    path = str(Path(filename).resolve()) + ".lock"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with _REGISTRY_MUTEX:
        entry = _LOCKS.setdefault(path, _LockState())
    deadline = time.monotonic() + timeout
    if not entry.mutex.acquire(timeout=max(0, timeout)):
        raise TimeoutError("Server state is busy: %s; retry after the current command finishes." % path)
    try:
        if entry.depth == 0:
            entry.descriptor = _acquire_process_lock(path, deadline)
        entry.depth += 1
        try:
            yield
        finally:
            entry.depth -= 1
            if entry.depth == 0:
                try:
                    _unlock(entry.descriptor)
                finally:
                    os.close(entry.descriptor)
                    entry.descriptor = None
    finally:
        entry.mutex.release()


def _after_fork():
    """A forked child must acquire its own locks instead of reusing ownership."""

    global _REGISTRY_MUTEX  # pylint: disable=global-statement
    for entry in _LOCKS.values():
        if entry.descriptor is not None:
            os.close(entry.descriptor)
    _LOCKS.clear()
    _REGISTRY_MUTEX = threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork)
