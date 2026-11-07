"""Standalone Windows update worker; uses only the standard library.

A copy of the installed executable runs this worker so Windows can release the
original executable. Each job has a private directory beside the installation.
The worker retains its executable and result there because Windows cannot remove
an executable while it is running. The directory can be deleted after completion.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


PARENT_TIMEOUT = 120
REPLACE_ATTEMPTS = 60
REPLACE_DELAY = 0.5


def file_sha256(path):
    """Hash an executable without loading the whole release into memory."""

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schedule_update(target, stage, checksum):
    """Launch an independent copy of the current executable to finish an update."""

    helper = stage / "helper.exe"
    shutil.copy2(target, helper)
    job_path = stage / "job.json"
    job_path.write_text(json.dumps({
        "target": str(target),
        "sha256": checksum,
        "parent_pid": os.getpid(),
    }), encoding="utf-8")
    result = stage / "result.txt"
    result.write_text("Update scheduled; waiting for the updater process to exit.\n", encoding="utf-8")
    with open(stage / "helper.log", "ab") as log:
        subprocess.Popen(
            [str(helper), "--_complete-self-update", str(job_path)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            close_fds=True,
            env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    return result


def _load_job(job_path):
    """Only accept a job whose payload and target share the staging filesystem."""

    if job_path.is_symlink() or job_path.parent.is_symlink():
        raise ValueError("Self-update job must not be a symbolic link.")
    stage = job_path.parent.resolve()
    if job_path.name != "job.json" or not stage.name.startswith(".alphagsm-self-update-"):
        raise ValueError("Invalid self-update staging directory.")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    target = Path(job["target"])
    if not target.is_absolute() or target.is_symlink() or target.resolve().parent != stage.parent:
        raise ValueError("Self-update target must be beside the staging directory.")
    if not target.is_file() or (stage / "replacement.exe").is_symlink():
        raise ValueError("Invalid self-update executable path.")
    if not isinstance(job["parent_pid"], int) or job["parent_pid"] <= 0:
        raise ValueError("Invalid self-update parent process.")
    if not re.fullmatch(r"[0-9a-f]{64}", job["sha256"]):
        raise ValueError("Invalid self-update SHA256 checksum.")
    return job, target


def complete_update(job_path):
    """Wait, verify, install with rollback, and record the actual final outcome."""

    job_path = Path(job_path)
    stage = job_path.parent
    replacement = stage / "replacement.exe"
    try:
        job, target = _load_job(job_path)
    except (OSError, ValueError, KeyError, TypeError) as ex:
        print("Invalid self-update job: %s" % (ex,), flush=True)
        return 1
    try:
        _wait_for_parent_exit(job["parent_pid"], PARENT_TIMEOUT)
        if file_sha256(replacement) != job["sha256"]:
            raise ValueError("Downloaded binary failed SHA256 verification.")
        _install_with_rollback(replacement, target, stage / "backup.exe")
    except (OSError, ValueError, KeyError, TypeError) as ex:
        outcome = "Update failed: %s\n" % (ex,)
        code = 1
    else:
        outcome = "Updated AlphaGSM binary successfully. You can restart AlphaGSM.\n"
        code = 0
    try:
        (stage / "result.txt").write_text(outcome, encoding="utf-8")
        # Preserve any backup after a failed rollback for operator recovery.
        replacement.unlink(missing_ok=True)
        (stage / "replacement.sha256").unlink(missing_ok=True)
    except OSError as ex:
        print("Unable to save update result or clean staging files: %s" % (ex,))
        code = 1
    print(outcome, end="", flush=True)
    return code


def _replace_with_retry(source, target):
    """Allow bounded time for the launcher and antivirus to release file handles."""

    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(REPLACE_DELAY)


def _install_with_rollback(replacement, target, backup):
    """Keep the old executable available until the new executable is installed."""

    if backup.exists():
        raise FileExistsError("An update backup already exists: %s" % (backup,))
    _replace_with_retry(target, backup)
    try:
        _replace_with_retry(replacement, target)
    except OSError as install_error:
        try:
            _replace_with_retry(backup, target)
        except OSError as rollback_error:
            raise OSError(
                "Installation failed (%s); unable to restore the original executable (%s). "
                "Restore it manually from %s" % (install_error, rollback_error, backup)
            ) from rollback_error
        raise
    backup.unlink()


def _wait_for_parent_exit(parent_pid, timeout):
    """Wait on a Windows process handle, without signalling or terminating it."""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x00100000, False, parent_pid)  # SYNCHRONIZE
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: process has already exited.
            return
        raise OSError(error, "Unable to wait for the updater process to exit.")
    try:
        result = kernel32.WaitForSingleObject(handle, int(timeout * 1000))
        if result == 0x00000102:  # WAIT_TIMEOUT
            raise TimeoutError("The updater process is still running; update was not applied.")
        if result != 0:  # WAIT_OBJECT_0
            raise OSError(ctypes.get_last_error(), "Waiting for the updater process failed.")
    finally:
        kernel32.CloseHandle(handle)
