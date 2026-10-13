"""Exercise terminal replies, real child input, exit codes and signal forwarding."""

import importlib
from pathlib import Path
import signal
import subprocess
import sys


def relay():
    path = Path(__file__).parents[3] / "src/gamemodules/btserver/terminal_relay.py"
    assert path.exists(), "Barotrauma's Docker console needs cursor-report emulation"
    return importlib.import_module("gamemodules.btserver.terminal_relay")


def test_cursor_reports_work_across_reads_without_unbounded_buffer():
    module = relay()
    codec = module.CursorReports()
    assert codec.feed(b"hello\x1b[6") == (b"hello", b"")
    assert codec.feed(b"nworld") == (b"world", b"\x1b[1;1R")
    output, replies = codec.feed(b"x" * 100000 + b"\x1b[")
    assert output == b"x" * 100000 and not replies
    assert len(codec.pending) <= 3


def test_real_pty_has_terminal_size_and_relays_input():
    module = relay()
    child = ('import os,tty,fcntl,termios,struct; tty.setraw(0,termios.TCSANOW); '
             'size=struct.unpack("HHHH",fcntl.ioctl(0,termios.TIOCGWINSZ,b"\\0"*8)); '
             'os.write(1,b"\\x1b[6n"); data=b""\n'
             'while b"hello\\n" not in data or b"\\x1b[1;1R" not in data: data+=os.read(0,1024)\n'
             'print("PTY_OK",os.isatty(0),size[:2],flush=True)')
    result = subprocess.run([sys.executable, module.__file__, sys.executable, "-c", child],
                            input=b"hello\n", capture_output=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    assert b"PTY_OK True (40, 120)" in result.stdout


def test_child_exit_code_and_termination_signal_are_preserved():
    module = relay()
    result = subprocess.run([sys.executable, module.__file__, sys.executable, "-c", "raise SystemExit(7)"],
                            capture_output=True, timeout=5, check=False)
    assert result.returncode == 7
    child = subprocess.Popen([sys.executable, module.__file__, sys.executable, "-c",
                              'import time; print("READY",flush=True); time.sleep(60)'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        assert b"READY" in child.stdout.readline()
        child.send_signal(signal.SIGTERM)
        assert child.wait(timeout=5) == 128 + signal.SIGTERM
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)
