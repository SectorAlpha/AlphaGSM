"""CI must not collect or invoke the local Steam-auth and BYO asset tests."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pytest_does_not_recurse_into_local_tests():
    config = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "norecursedirs" in config
    assert "local_tests" in config.split("norecursedirs", 1)[1]


def test_make_test_does_not_call_the_local_suite():
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    test_recipe = makefile.split("test: skills-check", 1)[1].split("\n\n", 1)[0]
    assert "local_tests" not in test_recipe
    assert "run_local_auth_tests.sh" not in test_recipe


def test_github_workflows_do_not_run_local_auth_tests():
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    for path in workflow_dir.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "local_tests" not in text
        assert "run_local_auth_tests.sh" not in text


def test_gitignore_covers_auth_material_and_local_runtime():
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("steam-auth/", ".local-tests/", ".alphagsm-private/", "ssfn"):
        assert pattern in text


def test_runner_refuses_ci_and_does_not_echo_a_rejected_secret():
    script = REPO_ROOT / "scripts" / "run_local_auth_tests.sh"
    env = os.environ.copy()
    env["CI"] = "true"
    env["PATH"] = os.environ["PATH"]
    ci_result = subprocess.run(
        ["bash", str(script), "unit"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert ci_result.returncode != 0
    assert "CI" in ci_result.stderr

    secret_env = os.environ.copy()
    secret_env.pop("CI", None)
    secret_env.pop("GITHUB_ACTIONS", None)
    secret = "not-a-real-secret"
    secret_result = subprocess.run(
        ["bash", str(script), "unit", "--password", secret],
        cwd=REPO_ROOT,
        env=secret_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert secret_result.returncode != 0
    assert secret not in secret_result.stdout
    assert secret not in secret_result.stderr


def test_local_suite_module_imports_under_the_runner_gate():
    env = os.environ.copy()
    env.pop("CI", None)
    env.pop("GITHUB_ACTIONS", None)
    env["ALPHAGSM_RUN_LOCAL_TESTS"] = "1"
    env["PYTHONPATH"] = "src:local_tests"
    env["ALPHAGSM_CONFIG_LOCATION"] = str(REPO_ROOT / "tests" / "alphagsm-test.conf")
    result = subprocess.run(
        [sys.executable, "-c", "import catalog; assert catalog.auth_servers() and catalog.byo_servers()"],
        cwd=REPO_ROOT / "local_tests",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
