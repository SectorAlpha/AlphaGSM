"""Portable opt-in Reclaimer lifecycle, shared by smoke and integration tests."""

import argparse
import configparser
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_lifecycle(work_dir, source, backend="process", image=None, timeout=180):
    """Drive only AlphaGSM commands against explicitly supplied owned game files."""
    # Import after adding the repository for direct Windows/Linux script use.
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.select_test_port import pick_free_port_group
    work_dir = Path(work_dir)
    home = work_dir / "home"
    home.mkdir(parents=True)
    install = work_dir / "server"
    config_path = work_dir / "alphagsm.conf"
    config = configparser.ConfigParser(interpolation=None)
    config.read_dict({
        "core": {"alphagsm_path": str(home), "userconf": str(home)},
        "server": {"datapath": str(home / "conf")},
        "downloader": {"db_path": str(home / "downloads/db"), "target_path": str(home / "downloads/files")},
        "runtime": {"backend": backend}, "process": {"backend": "subprocess"},
        "screen": {"screenlog_path": str(home / "logs"), "sessiontag": "ReclaimerSmoke#"},
    })
    with config_path.open("w", encoding="utf-8") as handle:
        config.write(handle)
    env = dict(os.environ, ALPHAGSM_CONFIG_LOCATION=str(config_path), PYTHONPATH=str(REPO_ROOT / "src"))
    port = pick_free_port_group(2)
    server_name = "it-reclaimer"

    def run(*arguments, check=True, command_timeout=600):
        result = subprocess.run([sys.executable, str(REPO_ROOT / "alphagsm"), server_name, *arguments],
                                env=env, capture_output=True, text=True, timeout=command_timeout, check=False)
        if check and result.returncode:
            raise AssertionError(f"AlphaGSM {arguments[0]} failed: {result.stdout}\n{result.stderr}")
        return result

    run("create", "projectreclaimer")
    if image:
        run("set", "image", image)
    run("setup", "-n", str(port), str(install), "--assets", str(source))
    run("assets", "check")
    started = True
    try:
        run("start")
        deadline = time.monotonic() + timeout
        last_error = ""
        while time.monotonic() < deadline:
            result = run("info", "--json", check=False, command_timeout=min(15, max(1, deadline - time.monotonic())))
            if result.returncode == 0:
                report = json.loads(result.stdout)
                assert report["protocol"] == "reclaimer_rcon" and report["port"] == port + 1, report
                assert report["players"] == 0 and report["max_players"] == 16, report
                assert report["map"].casefold() == "guardian", report
                break
            last_error = result.stderr or result.stdout
            time.sleep(1)
        else:
            logs = run("logs", "-n", "150", check=False)
            raise AssertionError("Reclaimer readiness timed out: " + last_error + "\n" + logs.stdout)
        run("status")
        run("query")
        run("info")
        run("info", "--json")
        run("stop")
        # A released listener must be bindable, and the real RCON query must fail.
        deadline = time.monotonic() + 90
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
                    udp.bind(("127.0.0.1", port))
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
                    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    tcp.bind(("127.0.0.1", port + 1))
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise AssertionError("Reclaimer listeners remain open after stop")
                time.sleep(1)
        assert run("query", check=False).returncode != 0
        assert "isn't running" in run("status").stdout
        started = False
        return report
    finally:
        if started:
            try:
                stop_result = run("stop", check=False, command_timeout=90)
                if stop_result.returncode or "isn't running" not in run("status", check=False, command_timeout=30).stdout:
                    run("kill", check=False, command_timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    run("kill", check=False, command_timeout=30)
                except (OSError, subprocess.TimeoutExpired):
                    pass  # Keep the original failure and preserve the work directory.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", default=os.environ.get("ALPHAGSM_RECLAIMER_ASSETS"))
    parser.add_argument("--runtime", choices=("process", "docker"), default=os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process"))
    parser.add_argument("--image", default=os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON"))
    args = parser.parse_args()
    if not args.assets:
        print("Project Reclaimer validation needs ALPHAGSM_RECLAIMER_ASSETS or --assets PATH to owned MCC files.")
        return 77
    work = tempfile.mkdtemp(prefix="alphagsm-reclaimer-", dir=os.environ.get("ALPHAGSM_WORK_DIR"))
    print("Validation files and logs: " + work)
    run_lifecycle(work, args.assets, args.runtime, args.image)
    print("Project Reclaimer lifecycle passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
