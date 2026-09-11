"""Job Object ownership before a suspended Windows child can create descendants."""

import importlib
from unittest.mock import Mock

import pytest


def test_windows_job_assigns_before_resuming_and_closes(monkeypatch):
    module = importlib.import_module("screen.windows_job")
    calls = []
    kernel = Mock()
    kernel.CreateJobObjectW.return_value = 11
    kernel.SetInformationJobObject.return_value = True
    kernel.OpenProcess.return_value = 22
    kernel.AssignProcessToJobObject.side_effect = lambda *_args: calls.append("assign") or True
    monkeypatch.setattr(module, "_kernel32", lambda: kernel)
    monkeypatch.setattr(module, "_resume_suspended_process", lambda *_args: calls.append("resume"))
    job = module.WindowsJob()
    limits = kernel.SetInformationJobObject.call_args.args[2]._obj
    assert limits.BasicLimitInformation.LimitFlags == 0x2000
    job.attach_and_resume(Mock(pid=123))
    assert calls == ["assign", "resume"]
    job.terminate()
    kernel.TerminateJobObject.assert_called_once_with(11, 1)
    job.close()
    job.close()
    assert kernel.CloseHandle.call_count == 2  # process handle and job handle


def test_windows_job_assignment_failure_never_resumes(monkeypatch):
    module = importlib.import_module("screen.windows_job")
    kernel = Mock()
    kernel.CreateJobObjectW.return_value = 11
    kernel.SetInformationJobObject.return_value = True
    kernel.OpenProcess.return_value = 22
    kernel.AssignProcessToJobObject.return_value = False
    resume = Mock()
    monkeypatch.setattr(module, "_kernel32", lambda: kernel)
    monkeypatch.setattr(module, "_resume_suspended_process", resume)
    monkeypatch.setattr(module.ctypes, "get_last_error", lambda: 5, raising=False)
    job = module.WindowsJob()
    try:
        with pytest.raises(OSError, match="assign"):
            job.attach_and_resume(Mock(pid=123))
        resume.assert_not_called()
    finally:
        job.close()
