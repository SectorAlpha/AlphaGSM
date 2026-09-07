#!/usr/bin/env python3
"""Accept a shipped binary from a clean home and unrelated working directory.

This stdlib-only controller and select_test_port.py can be copied outside the
checkout. The CLI is always the copied native executable, never a Python script.
Supply a downloaded real
Minecraft server jar to exercise setup, persistent console control, and shutdown.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

if __package__:
    from . import select_test_port
else:
    import select_test_port


def clean_environment(home, inherited=None):
    """Remove source, interpreter, and previous frozen-process configuration."""
    env = dict(os.environ if inherited is None else inherited)
    for key in list(env):
        if key.startswith(("PYTHON", "ALPHAGSM_", "_PYI_")) or key in (
            "VIRTUAL_ENV", "__PYVENV_LAUNCHER__",
        ):
            env.pop(key)
    env.update(HOME=str(home), USERPROFILE=str(home),
               LOCALAPPDATA=str(home / "AppData" / "Local"),
               APPDATA=str(home / "AppData" / "Roaming"))
    return env


class BinaryRunner:
    """Invoke only a relocated release executable with isolated user state."""

    def __init__(self, binary, work):
        self.work = Path(work).resolve()
        self.home = self.work / "home with spaces é"
        self.cwd = self.work / "unrelated working directory é"
        self.binary = self.work / "bin with spaces é" / Path(binary).name
        self.evidence = self.work / "evidence"
        for path in (self.home, self.cwd, self.binary.parent, self.evidence):
            path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, self.binary)
        self.env = clean_environment(self.home)
        self.last_server = None
        self.runtime = None
        self.userconf = None
        self._failure_captured = False

    def _write_evidence(self, filename, text, *, append=False):
        """Write only verifier-owned evidence, without traversing installed content."""
        try:
            with (self.evidence / filename).open("a" if append else "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            print(f"Could not save {filename}: {exc}", flush=True)

    def _record_command(self, command, result):
        """Keep the CLI transcript in the narrow artifact upload directory."""
        stdout = result.stdout.decode("utf-8", errors="replace") if isinstance(result.stdout, bytes) else result.stdout
        stderr = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else result.stderr
        output = f"$ {' '.join(command)}\nexit: {result.returncode}\n{stdout or ''}{stderr or ''}\n"
        self._write_evidence("commands.log", output, append=True)

    def run(self, *args, timeout=120, check=True):
        """Run a separate CLI process, failing on any unexpected command error."""
        command = [str(self.binary), *map(str, args)]
        if len(args) > 1 and not str(args[0]).startswith("-"):
            self.last_server = str(args[0])
        print(f"$ {self.binary.name} {' '.join(map(str, args))}", flush=True)
        try:
            result = subprocess.run(command, cwd=self.cwd, env=self.env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            self._record_command(command, subprocess.CompletedProcess(command, "timeout", exc.stdout, exc.stderr))
            raise
        except OSError as exc:
            self._record_command(command, subprocess.CompletedProcess(command, "launch error", "", str(exc)))
            raise
        self._record_command(command, result)
        if result.stdout:
            print(result.stdout.rstrip(), flush=True)
        if result.stderr:
            print(result.stderr.rstrip(), flush=True)
        if check and result.returncode:
            raise RuntimeError(f"CLI exited {result.returncode}: {result.stderr or result.stdout}")
        return result

    def capture_failure(self):
        """Capture live diagnostics once, before stop can remove the container."""
        if not self.last_server or self._failure_captured:
            return
        self._failure_captured = True
        for filename, args in (
            ("failure-doctor.json", ("doctor", "--json")),
            ("failure-console.log", ("logs", "-n", "100")),
        ):
            try:
                result = self.run(self.last_server, *args, check=False, timeout=30)
                self._write_evidence(filename, result.stdout)
                if result.stderr:
                    self._write_evidence("capture-errors.log", result.stderr + "\n", append=True)
            except (OSError, subprocess.SubprocessError) as exc:
                self._write_evidence("capture-errors.log", f"{filename}: {exc}\n", append=True)
        if self.runtime == "docker":
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "100", "alphagsm-" + self.last_server],
                    cwd=self.cwd, env=self.env, capture_output=True, text=True,
                    timeout=30, check=False,
                )
                self._write_evidence("failure-docker.log", (result.stdout or "") + (result.stderr or ""))
            except (OSError, subprocess.SubprocessError) as exc:
                self._write_evidence("capture-errors.log", f"Docker logs: {exc}\n", append=True)

    def capture_installation(self, name):
        """Copy the one known, redacted provenance record without a recursive glob."""
        if self.userconf is None:
            return
        path = self.userconf / "conf" / ".provenance" / f"{name}.installation.json"
        try:
            self._write_evidence("installation.json", path.read_text(encoding="utf-8"))
        except OSError as exc:
            self._write_evidence("capture-errors.log", f"Installation provenance: {exc}\n", append=True)

    def configure(self, runtime, backend):
        """Use the normal per-user config lookup without config environment overrides."""
        userconf = self.home / (
            "AppData/Local/alphagsm" if os.name == "nt" else ".alphagsm"
        )
        userconf.mkdir(parents=True, exist_ok=True)
        self.userconf = userconf
        self.runtime = runtime
        config = userconf / "alphagsm.conf"
        paths = (
            f"[core]\nalphagsm_path = {userconf}\n"
            f"[downloader]\ndb_path = {userconf / 'downloads/db.txt'}\n"
            f"target_path = {userconf / 'downloads/files'}\n"
        )
        config.write_text(
            paths +
            f"[server]\ndatapath = {userconf / 'conf'}\n"
            f"[runtime]\nbackend = {runtime}\n"
            f"[process]\nbackend = {backend}\n"
            "[docker]\nbackend = subprocess\n"
            f"[screen]\nscreenlog_path = {userconf / 'logs'}\n"
            "sessiontag = AlphaGSM-Binary#\nkeeplogs = 1\n",
            encoding="utf-8",
        )
        # The existing downloader reads system settings when no shared owner is
        # configured. A normal sibling config pins those paths without changing
        # production path semantics or depending on config environment overrides.
        # Config-free --version/help have already run before this is written.
        (self.binary.parent / "alphagsm.conf").write_text(paths, encoding="utf-8")
        return config


def verify_resources(runner):
    """Load each curated registry through real CLI commands without downloads."""
    curated = (
        ("teamfortress2", "metamod"), ("gmodserver", "ulib"),
        ("hl2dmserver", "sourcemod"), ("insserver", "sourcemod"),
        ("l4d2server", "sourcemod"), ("cssserver", "sourcemod"),
        ("minecraft.paper", "viaversion"), ("minecraft.waterfall", "viaversion"),
        ("minecraft.velocity", "viaversion"), ("terraria.tshock", "banguard"),
        ("scpslserver", "betterhelpcommand"), ("mtaserver", "pattach"),
    )
    for index, (module, family) in enumerate(curated):
        name = f"resource{index}"
        runner.run(name, "create", module)
        runner.run(name, "mod", "add", "curated", family)
        if module == "teamfortress2":
            runner.run(name, "map", "add", "curated", "cp_granary_pro_rc8")
    # A real config-backed set operation must read the packaged JSON template.
    runner.run("template", "create", "saleblazersserver")
    install = runner.work / "template-server"
    install.mkdir()
    runner.run("template", "set", "dir", install)
    runner.run("template", "set", "servername", "Binary template probe")
    payload = json.loads((install / "DedicatedServerConfig.json").read_text(encoding="utf-8"))
    assert payload["LobbyConfig"], "Saleblazers template was not materialized"
    runner.run("alias", "create", "tf2")
    # Both bulk paths must re-execute this isolated artifact, including on
    # Windows where subprocess pipes cannot use the POSIX multiplexer.
    listed = runner.run("2", "resource0", "resource1", "list").stdout.splitlines()
    assert set(listed) == {"resource0", "resource1"}, listed
    runner.run("2", "resource0", "resource1", "status")


def verify_windows_updater(runner):
    """Boot the native updater worker against an isolated, local replacement fixture."""
    fixture = runner.work / "updater-fixture"
    fixture.mkdir()
    target = fixture / "alphagsm.exe"
    target.write_bytes(b"old isolated update fixture")
    stage = Path(tempfile.mkdtemp(prefix=".alphagsm-self-update-", dir=fixture))
    helper = stage / "helper.exe"
    shutil.copy2(runner.binary, helper)
    replacement = b"replacement isolated update fixture"
    (stage / "replacement.exe").write_bytes(replacement)
    # Use an actual exited native child PID so the worker exercises parent wait.
    child = subprocess.Popen([str(runner.binary), "--version"], cwd=runner.cwd,
                             env=runner.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child.communicate(timeout=120)
    if child.returncode:
        raise RuntimeError("Updater acceptance parent fixture failed")
    manifest = stage / "job.json"
    manifest.write_text(json.dumps({
        "target": str(target), "sha256": hashlib.sha256(replacement).hexdigest(),
        "parent_pid": child.pid,
    }), encoding="utf-8")
    env = dict(runner.env, PYINSTALLER_RESET_ENVIRONMENT="1")
    result = subprocess.run([str(helper), "--_complete-self-update", str(manifest)],
                            cwd=runner.cwd, env=env, capture_output=True, text=True,
                            timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(f"Frozen updater helper failed: {result.stderr or result.stdout}")
    assert target.read_bytes() == replacement
    assert "Updated AlphaGSM binary successfully" in (stage / "result.txt").read_text(encoding="utf-8")
    assert not (stage / "replacement.exe").exists()
    assert not (stage / "backup.exe").exists()
    print("Frozen Windows updater helper acceptance passed", flush=True)


def free_port():
    """Use the shared non-ephemeral TCP/UDP loopback and wildcard port probe."""
    return select_test_port.pick_free_port_group(1)


def wait_for_info(runner, name, timeout):
    """Require the actual Minecraft status protocol through the artifact."""
    deadline = time.monotonic() + timeout
    last_result = None
    while time.monotonic() < deadline:
        last_result = runner.run(name, "info", "--json", check=False)
        if last_result.returncode == 0:
            payload = json.loads(last_result.stdout)
            if payload.get("protocol") == "slp":
                assert payload["players_online"] == 0
                return payload
        time.sleep(2)
    raise RuntimeError(f"Minecraft did not become ready: {last_result}")


def verify_lifecycle(runner, jar, java, timeout, runtime, image):
    """Exercise real provisioning and console control across separate CLI processes."""
    name = "binarymc"
    port = free_port()
    install = runner.work / "minecraft-server"
    jar_copy = runner.work / "server.jar"
    shutil.copy2(jar, jar_copy)
    runner.run(name, "create", "minecraft.vanilla")
    runner.run(name, "set", "javapath", java)
    if runtime == "docker" and image:
        runner.run(name, "set", "image", image)
    runner.run(name, "setup", "-n", "-l", port, install, "-u", jar_copy.as_uri(), timeout=timeout)
    runner.capture_installation(name)
    for filename in ("minecraft_server.jar", "eula.txt", "server.properties"):
        assert (install / filename).exists(), f"Missing setup output: {filename}"
    # Small real worlds keep acceptance practical on native release runners.
    with (install / "server.properties").open("a", encoding="utf-8") as handle:
        handle.write("\nonline-mode=false\nview-distance=2\nsimulation-distance=2\n")
    try:
        runner.run(name, "start", timeout=timeout)
        wait_for_info(runner, name, timeout)
        assert "Server is running" in runner.run(name, "status").stdout
        assert "Server port is open" in runner.run(name, "query").stdout
        assert "Server info (SLP" in runner.run(name, "info").stdout
        marker = "binary-console-control-confirmed"
        runner.run(name, "message", marker)
        # tellraw with no connected players has no message body in the log;
        # say records an observable console response even on an empty server.
        runner.run(name, "send", f"say {marker}")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            logs = runner.run(name, "logs", "-n", "100", check=False, timeout=30)
            if logs.returncode == 0 and marker in logs.stdout:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Message command did not reach the live server console")
    except Exception:
        runner.capture_failure()
        raise
    finally:
        runner.run(name, "stop", timeout=timeout, check=sys.exc_info()[0] is None)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                pass
        except OSError:
            break
        time.sleep(1)
    else:
        raise RuntimeError("Minecraft port remains open after stop")
    assert "isn't running" in runner.run(name, "status").stdout


def main():
    """Run portable artifact acceptance, preserving evidence when requested."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--minecraft-jar", type=Path)
    parser.add_argument("--resources-only", action="store_true")
    parser.add_argument("--java", default="java")
    parser.add_argument("--runtime", choices=("process", "docker"), default="process")
    parser.add_argument("--backend", choices=("subprocess", "screen", "tmux"), default="subprocess")
    parser.add_argument("--image", help="Explicit Docker runtime image to exercise")
    parser.add_argument("--expected-version")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--work-dir", type=Path, help="Empty directory to retain acceptance evidence")
    args = parser.parse_args()
    if not args.resources_only and not args.minecraft_jar:
        parser.error("--minecraft-jar is required for real lifecycle acceptance")
    if args.work_dir and args.work_dir.exists() and any(args.work_dir.iterdir()):
        parser.error("--work-dir must be empty")
    with tempfile.TemporaryDirectory(prefix="alphagsm-binary-") as temporary:
        runner = BinaryRunner(args.binary.resolve(), args.work_dir or Path(temporary))
        if os.name != "nt":
            runner.binary.parent.chmod(0o555)
        try:
            version = runner.run("--version").stdout.strip()
            if args.expected_version:
                assert version == f"AlphaGSM {args.expected_version}", version
            runner.run("--help")
            if os.name == "nt":
                verify_windows_updater(runner)
            if os.name != "nt":
                runner.binary.parent.chmod(0o755)
            runner.configure(args.runtime, args.backend)
            if os.name != "nt":
                runner.binary.parent.chmod(0o555)
            verify_resources(runner)
            if not args.resources_only:
                verify_lifecycle(runner, args.minecraft_jar.resolve(), args.java,
                                 args.timeout, args.runtime, args.image)
        except Exception:
            runner.capture_failure()
            raise
        finally:
            if os.name != "nt":
                runner.binary.parent.chmod(0o755)
        print("Standalone artifact acceptance passed", flush=True)


if __name__ == "__main__":
    main()
