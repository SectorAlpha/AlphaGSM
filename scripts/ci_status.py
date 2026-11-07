#!/usr/bin/env python3
"""Poll a GitHub Actions run and print compact failure triage."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Iterable


SUCCESS_CONCLUSIONS = {"success", "neutral", "skipped"}
FAILURE_CONCLUSIONS = {"failure", "timed_out", "startup_failure", "action_required"}
FAILURE_KEYWORDS = (
    "error",
    "failed",
    "failure",
    "exception",
    "traceback",
    "panic",
    "fatal",
    "timed out",
    "timeout",
    "returned non-zero",
    "return code",
    "no such file",
    "not found",
    "denied",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="GitHub Actions run id to monitor")
    parser.add_argument(
        "--repo",
        help="Optional [HOST/]OWNER/REPO override for gh",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=15.0,
        help="Seconds to sleep between polls when the run is still active",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print one snapshot and exit instead of polling until completion",
    )
    parser.add_argument(
        "--log-lines",
        type=int,
        default=80,
        help="Maximum number of log excerpt lines to print for a failed run",
    )
    return parser.parse_args(argv)


def _gh_base_command(repo: str | None = None) -> list[str]:
    command = ["gh"]
    if repo:
        command.extend(["-R", repo])
    return command


def _run_gh(args: Iterable[str], repo: str | None = None) -> str:
    command = [*_gh_base_command(repo), *args]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        message = f"gh command failed: {' '.join(command)}"
        if stdout:
            message = f"{message}\n{stdout}"
        if stderr:
            message = f"{message}\n{stderr}"
        raise RuntimeError(message)
    return result.stdout


def fetch_run(run_id: str, repo: str | None = None) -> dict[str, object]:
    payload = _run_gh(
        [
            "run",
            "view",
            run_id,
            "--json",
            "status,conclusion,workflowName,headBranch,headSha,url,jobs",
        ],
        repo=repo,
    )
    return json.loads(payload)


def fetch_failed_logs(run_id: str, repo: str | None = None) -> str:
    return _run_gh(["run", "view", run_id, "--log-failed"], repo=repo)


def failed_jobs(run: dict[str, object]) -> list[str]:
    jobs = run.get("jobs") or []
    names: list[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        conclusion = str(job.get("conclusion") or "").lower()
        if conclusion in SUCCESS_CONCLUSIONS or conclusion not in FAILURE_CONCLUSIONS:
            continue
        if str(job.get("status") or "").lower() == "completed":
            name = str(job.get("name") or "unknown job")
            names.append(name)
    return names


def extract_key_log_lines(log_text: str, limit: int = 80) -> list[str]:
    lines = log_text.splitlines()
    if not lines:
        return []

    selected: list[str] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        lower = line.lower()
        if not any(keyword in lower for keyword in FAILURE_KEYWORDS):
            continue
        start = max(0, index - 1)
        end = min(len(lines), index + 2)
        for nearby in lines[start:end]:
            if nearby not in seen:
                selected.append(nearby)
                seen.add(nearby)

    tail_start = max(0, len(lines) - max(1, limit // 2))
    for line in lines[tail_start:]:
        if line not in seen:
            selected.append(line)
            seen.add(line)

    if not selected:
        selected = lines[-limit:]
    elif len(selected) > limit:
        head_count = max(1, limit // 2)
        tail_count = max(0, limit - head_count)
        if tail_count:
            selected = selected[:head_count] + selected[-tail_count:]
        else:
            selected = selected[:head_count]
    return selected


def _run_summary(run_id: str, run: dict[str, object]) -> str:
    workflow = str(run.get("workflowName") or "workflow")
    branch = str(run.get("headBranch") or "?")
    sha = str(run.get("headSha") or "")[:8] or "unknown"
    status = str(run.get("status") or "unknown")
    conclusion = run.get("conclusion")
    url = str(run.get("url") or "")
    summary = f"run {run_id} {workflow} {branch}@{sha} status={status} conclusion={conclusion}"
    if url:
        summary = f"{summary} url={url}"
    return summary


def print_failed_run_details(run_id: str, run: dict[str, object], repo: str | None, log_lines: int) -> None:
    names = failed_jobs(run)
    if names:
        print("failed jobs:")
        for name in names:
            print(f"- {name}")

    log_text = fetch_failed_logs(run_id, repo=repo)
    key_lines = extract_key_log_lines(log_text, limit=log_lines)
    if key_lines:
        print("failed log excerpts:")
        for line in key_lines:
            print(line)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        while True:
            run = fetch_run(args.run_id, repo=args.repo)
            print(_run_summary(args.run_id, run))

            status = str(run.get("status") or "").lower()
            conclusion = str(run.get("conclusion") or "").lower()

            if status == "completed":
                if conclusion not in SUCCESS_CONCLUSIONS:
                    print_failed_run_details(args.run_id, run, args.repo, args.log_lines)
                    return 1
                return 0

            if args.once:
                return 0

            time.sleep(args.interval)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
