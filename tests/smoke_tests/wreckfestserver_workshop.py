"""Require native registration of an anonymously downloaded Wreckfest track."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

FIXTURE_ID = "3428792631"
FIXTURE_NAME = "Crazy 2025"
TRACK = "crazy_2000_classic"
NATIVE_PROBE = "/usr/local/lib/alphagsm/wreckfest-console-probe.exe"


def _windows_path(path):
    return "Z:" + str(path).replace("/", "\\")


def capture_native_registry(install, *, container=None, wineprefix=None,
                            helper_path=None, timeout_seconds=45, runner=None):
    """Read a fresh real Win32 console response from the selected private prefix.

    The bounded helper sends only tracks. It matches the exact executable path,
    clears stale screen contents before input, and creates a unique new file.
    AlphaGSM continues to own every lifecycle action.
    """
    install = Path(install).resolve()
    executables = [install / name for name in ("Wreckfest_x64.exe", "Wreckfest.exe")
                   if (install / name).is_file()]
    assert executables, "Wreckfest native capture needs an installed executable"
    executable = executables[0]
    relative = Path(".alphagsm/native-probes") / (uuid.uuid4().hex + ".log")
    output = install / relative
    assert all(not path.is_symlink() for path in (install / '.alphagsm', output.parent)), (
        "Native capture directory must not be a symlink")
    output.parent.mkdir(parents=True, exist_ok=True)
    assert not output.exists(), "Native capture file must be fresh"
    helper = helper_path or os.environ.get("ALPHAGSM_WRECKFEST_CONSOLE_PROBE", NATIVE_PROBE)
    prefix = Path(wineprefix or install / ".alphagsm-wineprefix").resolve()
    if container:
        mounted = Path("/srv/server")
        prefix_relative = prefix.relative_to(install)
        command = ["docker", "exec", "--env", "WINEPREFIX=" + str(mounted / prefix_relative),
                   "--env", "WINEDEBUG=-all", container, "wine", helper,
                   _windows_path(mounted / executable.name), _windows_path(mounted / relative)]
    else:
        from utils import proton
        assert Path(helper).is_file(), "Install the compiled Wreckfest native console probe or set ALPHAGSM_WRECKFEST_CONSOLE_PROBE"
        command = proton.wrap_command([helper, _windows_path(executable), _windows_path(output)],
                                      wineprefix=str(prefix), prefer_proton=True)
    execute = runner or subprocess.run
    try:
        execute(command, capture_output=True, text=True, check=True, timeout=timeout_seconds)
        assert output.is_file() and not output.is_symlink(), "Native console probe did not create fresh evidence"
        assert output.stat().st_size <= 1024 * 1024, "Native console probe output exceeds 1 MiB"
        evidence = output.read_text(encoding="utf-8", errors="replace")
        assert_workshop_loaded(evidence)
        return evidence
    except (AssertionError, subprocess.SubprocessError):
        if output.is_file() and not output.is_symlink():
            with output.open('rb') as capture:
                tail = capture.read(8000)
            print(f"[diagnostic] Fresh native Win32 console probe: {tail!r}")
        raise


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
    for match in re.finditer(r"(?m)^[ \t]*>?[ \t]*Tracks:[ \t]*\r?(?:\n|$)", log_text):
        header = match
    assert header is not None, "Native Tracks: registry section is missing"
    found = False
    row_count = 0
    for line in log_text[header.end():].splitlines():
        row = re.fullmatch(r"[ \t]*>?[ \t]+([A-Za-z0-9_-]+)[ \t]+\(([^()\r\n]+)\)[ \t]*", line)
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
    latest = ""

    def fresh_output(remaining):
        nonlocal latest
        output = fetch_output(remaining)
        assert output.startswith(before), "Native console capture rotated during the Tracks request"
        latest = output[len(before):]
        return latest

    try:
        return wait_for_workshop_loaded(fresh_output, max(0, deadline - clock()), clock=clock, sleep=sleep)
    except AssertionError:
        # repr exposes terminal controls and empty captures in remote job logs;
        # these diagnostic bytes never replace the required native registry.
        print(f"[diagnostic] Wreckfest console before tracks: {len(before)} chars; tail={before[-2000:]!r}")
        print(f"[diagnostic] Wreckfest fresh tracks response: {len(latest)} chars; tail={latest[-8000:]!r}")
        raise


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
    parser.add_argument("--install", type=Path)
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    if args.install:
        assert args.server, "Native runtime capture requires the AlphaGSM server name"
        doctor = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[2] / "alphagsm"),
             args.server, "doctor", "--json"],
            capture_output=True, text=True, check=True, timeout=15,
        )
        runtime = json.loads(doctor.stdout)["runtime"]
        container = runtime.get("container_name") if runtime.get("resolved_runtime") == "docker" else None
        output = capture_native_registry(args.install, container=container)
        args.log.write_text(output, encoding="utf-8")
        return
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
