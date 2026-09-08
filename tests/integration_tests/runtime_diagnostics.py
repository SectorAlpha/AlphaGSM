"""Read-only, bounded Docker evidence for failed integration readiness.

Returned output can contain game log text; callers must apply their normal
diagnostic redaction before printing or persisting it.
"""

import inspect
import json
import os
from pathlib import Path
import subprocess
import uuid


def collect_process_diagnostics(proc_root="/proc", home_roots=None):
    """Read wait states and selected Steam log tails, never argv or environment."""

    def read_text(path, limit=4096):
        try:
            with path.open("rb") as handle:
                return handle.read(limit).decode("utf-8", errors="replace").strip()
        except OSError as exc:
            return f"unavailable: {exc}"

    process_rows = []
    for process in sorted(Path(proc_root).glob("[0-9]*"))[:32]:
        row = {"pid": int(process.name), "comm": read_text(process / "comm")}
        row["status"] = [
            line for line in read_text(process / "status").splitlines()
            if line.startswith(("State:", "Uid:", "Threads:", "Seccomp:", "NoNewPrivs:", "CapEff:"))
        ]
        row["wchan"] = read_text(process / "wchan")
        try:
            row["stdin"] = os.readlink(process / "fd" / "0")
        except OSError as exc:
            row["stdin"] = f"unavailable: {exc}"
        row["threads"] = [
            {"tid": int(thread.name), "wchan": read_text(thread / "wchan")}
            for thread in sorted((process / "task").glob("[0-9]*"))[:16]
        ]
        row["steam_libraries"] = sorted({
            line.split()[-1] for line in read_text(process / "maps", 65536).splitlines()
            if "/" in line and any(name in line for name in (
                "steamclient.so", "libsteam_api.so", "libtier0_s.so", "libvstdlib_s.so"))
        })
        process_rows.append(row)

    if home_roots is None:
        home_roots = [os.environ.get("HOME", "/root"), "/root", "/home/alphagsm", "/home/steam"]
    home_roots = list(dict.fromkeys(str(home) for home in home_roots))[:4]
    steam_state = [
        {"path": str(Path(home) / relative), "exists": (Path(home) / relative).exists()}
        for home in home_roots
        for relative in (
            ".steam/sdk32/steamclient.so", ".steam/sdk64/steamclient.so",
            ".steam/steam/steamapps/libraryfolders.vdf",
            ".local/share/Steam/steamapps/libraryfolders.vdf",
        )
    ]
    log_rows = []
    seen = set()
    for home in home_roots:
        for relative in (".steam/steam/logs", ".steam/steamcmd/logs", "Steam/logs", ".local/share/Steam/logs"):
            for filename in ("connection_log.txt", "console_log.txt", "stderr.txt", "appinfo_log.txt"):
                path = Path(home) / relative / filename
                if len(log_rows) >= 8 or str(path) in seen or not path.is_file():
                    continue
                seen.add(str(path))
                try:
                    with path.open("rb") as handle:
                        handle.seek(0, os.SEEK_END)
                        handle.seek(max(0, handle.tell() - 8192))
                        tail = handle.read(8192).decode("utf-8", errors="replace")
                    tail = "".join(tail.splitlines(keepends=True)[-30:])
                except OSError as exc:
                    tail = f"unavailable: {exc}"
                log_rows.append({"path": str(path), "tail": tail})
    return {"processes": process_rows, "steam_logs": log_rows, "steam_state": steam_state}


def collect_source_stacks(proc_root="/proc"):
    """Briefly attach to stalled Source engines; omit arguments and locals."""

    results = []
    for process in sorted(Path(proc_root).glob("[0-9]*"))[:32]:
        try:
            name = (process / "comm").read_text().strip()
        except OSError:
            continue
        if name not in ("srcds_linux", "srcds_linux64", "hlds_linux"):
            continue
        command = [
            "gdb", "-q", "-nx", "-nh", "-batch",
            "-iex", "set auto-load off", "-iex", "set debuginfod enabled off",
            "-iex", "set print frame-arguments none", "-iex", "set print entry-values no",
            "-ex", "set sysroot " + str(process / "root"),
            "-ex", "attach " + process.name,
            "-ex", "thread apply all bt 12", "-ex", "detach",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=8)
            output = (result.stdout + result.stderr)[-24000:]
            returncode = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            output, returncode = "Stack capture unavailable: " + type(exc).__name__, 1
        results.append({"pid": int(process.name), "comm": name, "returncode": returncode, "stack": output})
        if len(results) == 2:
            break
    return results


def collect_docker_runtime_diagnostics(container_name, *, run_command=subprocess.run):
    """Return bounded command results, including unavailable/exited containers."""

    def run(command, timeout=10):
        try:
            return run_command(command, capture_output=True, text=True, check=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            return subprocess.CompletedProcess(command, 124, output, f"Diagnostic timed out after {timeout}s")
        except OSError as exc:
            return subprocess.CompletedProcess(command, 1, "", f"Diagnostic unavailable: {exc}")

    if not isinstance(container_name, str) or not container_name or container_name.startswith("-"):
        return []
    # Inspect only State, excluding environment, labels and other operator data.
    state = run(["docker", "inspect", "--format", "{{json .State}}", container_name])
    results = [("Docker container state", state)]
    if state.returncode != 0:
        return results
    try:
        running = json.loads(state.stdout).get("Running") is True
    except (ValueError, AttributeError):
        running = False
    if running:
        script = (
            "import json, os\nfrom pathlib import Path\n"
            + inspect.getsource(collect_process_diagnostics)
            + "\nprint(json.dumps(collect_process_diagnostics()))\n"
        )
        results.append(("Docker process wait states and Steam logs", run([
            "docker", "exec", container_name, "python3", "-c", script,
        ])))
        image = os.environ.get("ALPHAGSM_DIAGNOSTIC_IMAGE")
        try:
            processes = json.loads(results[-1][1].stdout).get("processes", [])
        except (ValueError, AttributeError):
            processes = []
        if image and any(isinstance(row, dict) and row.get("comm") in (
            "srcds_linux", "srcds_linux64", "hlds_linux"
        ) for row in processes):
            results.append(("Docker daemon version", run([
                "docker", "version", "--format", "{{json .Server}}",
            ])))
            script = (
                "import json, subprocess\nfrom pathlib import Path\n"
                + inspect.getsource(collect_source_stacks)
                + "\nprint(json.dumps(collect_source_stacks()))\n"
            )
            # Only the short-lived debugger gets ptrace permission. The game
            # retains its original capabilities, seccomp profile and network.
            probe_name = "alphagsm-diagnostic-" + uuid.uuid4().hex
            try:
                results.append(("Source native stack traces", run([
                    "docker", "run", "--rm", "--pull", "never", "--name", probe_name,
                    "--pid", "container:" + container_name, "--network", "none",
                    "--cap-drop", "ALL", "--cap-add", "SYS_PTRACE",
                    "--security-opt", "no-new-privileges", "--read-only",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
                    "--entrypoint", "python3", image, "-c", script,
                ], timeout=30)))
            finally:
                # Killing a timed-out Docker CLI does not stop its container.
                run(["docker", "rm", "-f", probe_name])
    return results
