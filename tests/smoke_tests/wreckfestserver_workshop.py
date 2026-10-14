"""Require native registration of an anonymously downloaded Wreckfest track."""

import argparse
from pathlib import Path
import re
import subprocess
import sys
import time

FIXTURE_ID = "3428792631"
FIXTURE_NAME = "Crazy 2025"
TRACK = "crazy_2000_classic"


def assert_workshop_loaded(log_text):
    """Require the exact event in the latest native Tracks registry response.

    The caller must supply a fresh capture. This validates response syntax;
    it cannot establish when arbitrary supplied text was produced.
    """
    assert len(log_text) <= 1024 * 1024, "Native track response exceeds 1 MiB"
    # Wine's real terminal emits ANSI styling around the native response.
    log_text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", log_text)
    assert not re.search(r"(?i)\b(?:unknown command|error|failed to load|not found)\b", log_text), (
        "Native track capture contains a command or load error")
    header = None
    for match in re.finditer(r"(?m)^[ \t]*Tracks:[ \t]*\r?(?:\n|$)", log_text):
        header = match
    assert header is not None, "Native Tracks: registry section is missing"
    found = False
    row_count = 0
    for line in log_text[header.end():].splitlines():
        row = re.fullmatch(r"[ \t]+([A-Za-z0-9_-]+)[ \t]+\(([^()\r\n]+)\)[ \t]*", line)
        if row is None:
            break
        assert row_count < 1024, "Native Tracks: registry exceeds 1024 rows"
        row_count += 1
        if row.group(1) == TRACK and row.group(2).strip():
            found = True
    assert found, "Native track registry did not list the exact Workshop event"


def capture_workshop_registry(fetch_output, send_command, timeout_seconds=90, *,
                              clock=time.monotonic, sleep=time.sleep):
    """Issue tracks and accept only output appended after that fresh request."""
    deadline = clock() + timeout_seconds
    before = fetch_output(timeout_seconds)
    send_command()

    def fresh_output(remaining):
        output = fetch_output(remaining)
        assert output.startswith(before), "Native console capture rotated during the Tracks request"
        return output[len(before):]

    return wait_for_workshop_loaded(fresh_output, max(0, deadline - clock()), clock=clock, sleep=sleep)


def wait_for_workshop_loaded(fetch_output, timeout_seconds=90, *,
                             clock=time.monotonic, sleep=time.sleep):
    """Poll complete fresh captures, giving each fetch its remaining time budget."""
    deadline = clock() + timeout_seconds
    last_error = "No native track registry response received"
    while (remaining := deadline - clock()) > 0:
        output = fetch_output(remaining)
        try:
            assert_workshop_loaded(output)
        except AssertionError as error:
            last_error = str(error)
        else:
            if clock() <= deadline:
                return output
            last_error = "Native track registry response arrived after the deadline"
        remaining = deadline - clock()
        if remaining > 0:
            sleep(min(1, remaining))
    raise AssertionError("Timed out waiting for native Workshop registry: " + last_error)


def main():
    """Validate fresh native console output captured by a smoke run."""
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--server")
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    if args.server:
        command = [sys.executable, str(Path(__file__).resolve().parents[2] / "alphagsm"), args.server]
        def fetch(remaining):
            result = subprocess.run(
                [*command, "logs", "-n", "2000"],
                capture_output=True, text=True, check=True, timeout=min(15, remaining),
            )
            return result.stdout
        def send():
            subprocess.run([*command, "send", "tracks"], capture_output=True, text=True,
                           check=True, timeout=min(15, args.timeout))
        output = capture_workshop_registry(fetch, send, timeout_seconds=args.timeout)
        args.log.write_text(output, encoding="utf-8")
    else:
        assert_workshop_loaded(args.log.read_text(errors="replace"))


if __name__ == "__main__":
    main()
