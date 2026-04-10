"""Unit tests for the root-level Docker wrapper."""

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "alphagsm-docker"


def _write_fake_docker(bin_dir):
    fake_docker = bin_dir / "docker"
    fake_docker.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "log_path = Path(os.environ['FAKE_DOCKER_LOG'])",
                "entry = {'argv': sys.argv[1:], 'alphagsm_home': os.environ.get('ALPHAGSM_HOME', '')}",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps(entry) + '\\n')",
                "args = sys.argv[1:]",
                "if args[:2] == ['compose', 'version']:",
                "    sys.exit(0)",
                "if 'ps' in args and '--services' in args:",
                "    sys.stdout.write(os.environ.get('FAKE_COMPOSE_PS_OUTPUT', ''))",
                "    sys.exit(0)",
                "if 'up' in args:",
                "    sys.exit(0)",
                "if 'config' in args:",
                "    sys.stdout.write('services:\\n  alphagsm: {}\\n')",
                "    sys.exit(0)",
                "if 'exec' in args:",
                "    exec_index = args.index('exec')",
                "    forwarded = args[exec_index + 1:]",
                "    sys.stdout.write('FORWARDED:' + ' '.join(forwarded) + '\\n')",
                "    sys.exit(0)",
                "if 'down' in args or 'logs' in args:",
                "    sys.exit(0)",
                "sys.stderr.write('Unhandled fake docker args: ' + ' '.join(args) + '\\n')",
                "sys.exit(1)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)


def _run_wrapper(tmp_path, *args, ps_output=""):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "docker.log"
    state_dir = tmp_path / "state"
    _write_fake_docker(bin_dir)

    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["FAKE_DOCKER_LOG"] = str(log_path)
    env["FAKE_COMPOSE_PS_OUTPUT"] = ps_output
    env["ALPHAGSM_HOME"] = str(state_dir)

    result = subprocess.run(
        ["bash", str(WRAPPER), *args],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )
    log_entries = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return result, state_dir, log_entries


def test_wrapper_bootstraps_config_before_compose_command(tmp_path):
    result, state_dir, log_entries = _run_wrapper(tmp_path, "compose", "config")

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    config_text = (state_dir / "alphagsm.conf").read_text(encoding="utf-8")
    assert f"alphagsm_path = {state_dir}/home" in config_text
    assert any(entry["argv"][:2] == ["compose", "version"] for entry in log_entries)
    assert any("config" in entry["argv"] for entry in log_entries)


def test_wrapper_starts_manager_and_forwards_alphagsm_command(tmp_path):
    result, state_dir, log_entries = _run_wrapper(
        tmp_path,
        "demo",
        "create",
        "minecraft.vanilla",
        ps_output="",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (state_dir / "alphagsm.conf").exists()
    assert any("ps" in entry["argv"] for entry in log_entries)
    assert any("up" in entry["argv"] for entry in log_entries)
    assert any(
        entry["argv"][-6:] == [
            "exec",
            "alphagsm",
            "python",
            "alphagsm",
            "demo",
            "create",
            "minecraft.vanilla",
        ][-6:]
        and entry["alphagsm_home"] == str(state_dir)
        for entry in log_entries
    )
    assert "FORWARDED:-T alphagsm python alphagsm demo create minecraft.vanilla" in result.stdout