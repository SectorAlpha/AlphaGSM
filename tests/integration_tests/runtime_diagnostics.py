"""Read-only, bounded Docker evidence for failed integration readiness.

Returned output can contain game log text; callers must apply their normal
diagnostic redaction before printing or persisting it.
"""

import inspect
import json
import os
from pathlib import Path
import subprocess


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
            if line.startswith(("State:", "Uid:", "Threads:"))
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


def collect_docker_runtime_diagnostics(container_name, *, run_command=subprocess.run):
    """Return bounded command results, including unavailable/exited containers."""

    def run(command):
        try:
            return run_command(command, capture_output=True, text=True, check=False, timeout=10)
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            return subprocess.CompletedProcess(command, 124, output, "Diagnostic timed out after 10s")
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
    return results
