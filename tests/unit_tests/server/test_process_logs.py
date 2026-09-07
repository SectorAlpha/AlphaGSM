"""Process logs remain available without Unix command-line utilities."""

from types import SimpleNamespace

import pytest

import server.runtime as runtime_module


@pytest.fixture
def process_log(tmp_path, monkeypatch):
    path = tmp_path / "server.log"
    monkeypatch.setattr(runtime_module.screen, "logpath", lambda name: str(path))
    monkeypatch.setattr(runtime_module.sp, "run",
                        lambda *args, **kwargs: pytest.fail("logs must not launch a subprocess"))
    return path


@pytest.mark.parametrize('content,lines,expected', [
    ("first\n雪 café\nlast".encode('utf-8'), 2, "雪 café\nlast"),
    (b"old\nmalformed \xff\n", 1, "malformed \ufffd\n"),
    (b"first\r\nlast\r\n", 1, "last\n"),
    (b"first\nlast\n", 0, ""),
    (b"only\n", 5, "only\n"),
    (b"", 5, ""),
])
def test_logs_print_requested_tail(process_log, capsys, content, lines, expected):
    process_log.write_bytes(content)
    runtime_module.ProcessRuntime().show_logs(SimpleNamespace(name='fixture'), lines=lines)
    assert capsys.readouterr().out == expected


def test_logs_default_keeps_last_fifty_lines(process_log, capsys):
    process_log.write_text(''.join(f'{number}\n' for number in range(5000)), encoding='utf-8')
    runtime_module.ProcessRuntime().show_logs(SimpleNamespace(name='fixture'))
    assert capsys.readouterr().out == ''.join(f'{number}\n' for number in range(4950, 5000))


@pytest.mark.parametrize('lines', [-1, 2.5, 'ten', None])
def test_logs_reject_invalid_line_count(process_log, lines):
    process_log.write_text('line\n', encoding='utf-8')
    with pytest.raises(runtime_module.RuntimeError, match='nonnegative integer'):
        runtime_module.ProcessRuntime().show_logs(SimpleNamespace(name='fixture'), lines=lines)


def test_logs_missing_file_reports_runtime_error(process_log):
    with pytest.raises(runtime_module.RuntimeError, match='No log file'):
        runtime_module.ProcessRuntime().show_logs(SimpleNamespace(name='fixture'))


def test_logs_read_error_reports_runtime_error(process_log, monkeypatch):
    process_log.write_text('line\n', encoding='utf-8')

    def fail_open(*args, **kwargs):
        raise PermissionError('access denied')

    monkeypatch.setattr('builtins.open', fail_open)
    with pytest.raises(runtime_module.RuntimeError, match='Failed to read log file'):
        runtime_module.ProcessRuntime().show_logs(SimpleNamespace(name='fixture'))
