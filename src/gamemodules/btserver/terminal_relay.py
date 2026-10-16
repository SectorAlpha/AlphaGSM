"""Minimal bounded cursor-report terminal for Barotrauma's .NET Docker console."""

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios


class CursorReports:
    """Reply to split DSR queries while retaining at most three pending bytes."""

    def __init__(self):
        self.pending = b""

    def feed(self, chunk):
        """Return output bytes and safe cursor replies; other escapes pass through."""
        query = b"\x1b[6n"
        data = self.pending + chunk
        replies = b"\x1b[1;1R" * data.count(query)
        data = data.replace(query, b"")
        retained = 0
        for size in range(1, len(query)):
            if data.endswith(query[:size]):
                retained = size
        self.pending = data[-retained:] if retained else b""
        return data[:-retained] if retained else data, replies


def _pump(master, pid):
    """Forward input and answer cursor queries without collecting console history."""
    codec = CursorReports()
    inputs = [master, 0]
    while True:
        readable, _, _ = select.select(inputs, [], [], 0.2)
        for descriptor in readable:
            try:
                data = os.read(descriptor, 65536)
            except OSError as exc:
                if descriptor == master and exc.errno == errno.EIO:
                    return
                raise
            if not data:
                if descriptor == master:
                    return
                inputs.remove(0)
                continue
            if descriptor == 0:
                os.write(master, data)
            else:
                output, replies = codec.feed(data)
                if replies:
                    os.write(master, replies)
                sys.stdout.buffer.write(output)
                sys.stdout.buffer.flush()
        if not readable:
            # The PTY itself normally signals EIO on exit; kill(pid, 0) avoids
            # consuming the child's wait status before the caller records it.
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return


def main(arguments=None):
    """Run the dedicated server with real terminal input and preserve child exit."""
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    if not arguments:
        raise SystemExit("A dedicated server command is required")
    pid, master = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
        try:
            os.execvp(arguments[0], arguments)
        except OSError as exc:
            print(str(exc), file=sys.stderr, flush=True)
            os._exit(127)  # pylint: disable=protected-access
    previous_handlers = {}
    def forward(signum, _frame):
        try:
            os.killpg(pid, signum)
        except ProcessLookupError:
            pass
    try:
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous_handlers[signum] = signal.signal(signum, forward)
        _pump(master, pid)
    except BaseException:
        forward(signal.SIGTERM, None)
        raise
    finally:
        os.close(master)
        _, status = os.waitpid(pid, 0)
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    code = os.waitstatus_to_exitcode(status)
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    raise SystemExit(main())
