"""Own a Windows server tree before its initially suspended process can run.

The supervisor keeps the only Job Object handle. Windows kills all members if
that handle closes, including when the supervisor crashes. A child is assigned
while CREATE_SUSPENDED prevents it from spawning unowned descendants; documented
Toolhelp and ResumeThread APIs then resume its initial thread.
"""

import ctypes
from ctypes import wintypes

CREATE_SUSPENDED = 0x00000004


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits), ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _ThreadEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG), ("dwFlags", wintypes.DWORD),
    ]


def _kernel32():
    """Declare pointer-sized handle signatures explicitly for 64-bit Windows."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        "CreateToolhelp32Snapshot": ([wintypes.DWORD, wintypes.DWORD], wintypes.HANDLE),
        "Thread32First": ([wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)], wintypes.BOOL),
        "Thread32Next": ([wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)], wintypes.BOOL),
        "OpenThread": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        "ResumeThread": ([wintypes.HANDLE], wintypes.DWORD),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes = arguments
        function.restype = result
    return kernel


def _raise_windows_error(message):
    raise OSError(ctypes.get_last_error(), message)


def _resume_suspended_process(kernel, pid):
    """Find and resume the only initial thread of a newly suspended process."""
    snapshot = kernel.CreateToolhelp32Snapshot(0x00000004, 0)  # TH32CS_SNAPTHREAD
    if snapshot == ctypes.c_void_p(-1).value:
        _raise_windows_error("Cannot enumerate suspended server threads")
    try:
        entry = _ThreadEntry()
        entry.dwSize = ctypes.sizeof(entry)
        found = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == pid:
                thread = kernel.OpenThread(0x0002, False, entry.th32ThreadID)  # THREAD_SUSPEND_RESUME
                if not thread:
                    _raise_windows_error("Cannot open suspended server thread")
                try:
                    if kernel.ResumeThread(thread) == 0xFFFFFFFF:
                        _raise_windows_error("Cannot resume suspended server thread")
                    return
                finally:
                    kernel.CloseHandle(thread)
            found = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        raise OSError("Cannot find the suspended server's initial thread")
    finally:
        kernel.CloseHandle(snapshot)


class WindowsJob:
    """Keep descendants owned even after their original parent has exited."""

    def __init__(self):
        self.kernel = _kernel32()
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            _raise_windows_error("Cannot create Windows server Job Object")
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "Cannot configure Windows server Job Object")

    def attach_and_resume(self, process):
        """Associate a suspended child before allowing any of its code to run."""
        handle = self.kernel.OpenProcess(0x0101, False, process.pid)  # PROCESS_SET_QUOTA | PROCESS_TERMINATE
        if not handle:
            _raise_windows_error("Cannot open suspended server process")
        try:
            if not self.kernel.AssignProcessToJobObject(self.handle, handle):
                _raise_windows_error("Cannot assign server to its Windows Job Object")
        finally:
            self.kernel.CloseHandle(handle)
        _resume_suspended_process(self.kernel, process.pid)

    def terminate(self):
        """Terminate every member, including children whose parent has exited."""
        if self.handle and not self.kernel.TerminateJobObject(self.handle, 1):
            _raise_windows_error("Cannot terminate Windows server Job Object")

    def close(self):
        """Release the only job handle; the kernel also terminates all members."""
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
