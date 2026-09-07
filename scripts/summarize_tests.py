#!/usr/bin/env python3
"""Fail-closed required CI gate: job outcomes, complete artifacts, one recheck."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

from collect_integration_rechecks import collect_failed_rechecks, pytest_nodeid_from_testcase


REQUIRED_JOBS = (
    'build lint unit-test coverage binary-build-smoke classify-changes '
    'discover-smoke-tests discover-integration-tests build-integration-image '
    'build-java-runtime build-simple-tcp-runtime build-steamcmd-linux-runtime '
    'build-wine-proton-runtime backend-smoke-test backend-integration-test '
    'windows-minecraft-integration macos-minecraft-integration collect-integration-rechecks'
).split()


def read_report(path: Path) -> dict[str, str]:
    """Reject missing, malformed, empty, duplicate, or truncated JUnit reports."""
    root = ET.parse(path).getroot()
    if root.tag not in ('testsuites', 'testsuite'):
        raise ValueError(f'Invalid JUnit root: {path}')
    cases = list(root.iter('testcase'))
    if not cases:
        raise ValueError(f'Empty JUnit report: {path}')
    for suite in root.iter('testsuite'):
        suite_cases = list(suite.iter('testcase'))
        counts = {'tests': len(suite_cases)}
        for attribute, tag in (('failures', 'failure'), ('errors', 'error'), ('skipped', 'skipped')):
            counts[attribute] = sum(case.find(tag) is not None for case in suite_cases)
        for attribute, count in counts.items():
            if attribute in suite.attrib and int(suite.attrib[attribute]) != count:
                raise ValueError(f'Inconsistent JUnit {attribute} count: {path}')
    results = {}
    for case in cases:
        nodeid = pytest_nodeid_from_testcase(case)
        if not nodeid or nodeid in results:
            raise ValueError(f'Missing or duplicate testcase identity: {path}: {nodeid}')
        outcome = 'passed'
        if case.find('failure') is not None or case.find('error') is not None:
            outcome = 'failed'
        elif case.find('skipped') is not None:
            outcome = 'skipped'
        results[nodeid] = outcome
    return results


def summarize(artifacts: Path, needs: dict) -> list[str]:
    """Return blocking errors; retain initial failures in the printed audit trail."""
    errors = []
    expected_files = set()
    initial_failures = set()
    routing = needs.get('classify-changes', {}).get('outputs', {})

    def require_job(job, expected='success'):
        result = needs.get(job, {}).get('result', 'missing')
        if result != expected:
            errors.append(f'{job}: expected {expected}, got {result}')

    def read(artifact, filename):
        path = artifacts / artifact / filename
        expected_files.add(path)
        try:
            results = read_report(path)
            counts = {status: list(results.values()).count(status) for status in ('passed', 'skipped', 'failed')}
            print(f'{artifact}/{filename}: {counts}')
            return results
        except (OSError, ValueError, ET.ParseError) as exc:
            errors.append(f'{path}: {exc}')
            return {}

    for job in REQUIRED_JOBS:
        require_job(job)
    if routing.get('game_test_mode') not in ('skip', 'targeted', 'all'):
        errors.append('Missing or invalid routing mode')

    for kind in ('smoke', 'integration'):
        for runner_class in ('standard', 'heavy'):
            lane = f'{kind}_{runner_class}'
            rows = json.loads(routing[f'{lane}_matrix'])['include']
            selected = bool(rows)
            if routing.get(f'has_{lane}_tests') != str(selected).lower():
                errors.append(f'{lane}: matrix and selection flag disagree')
            if routing.get('game_test_mode') == 'skip' and selected:
                errors.append(f'{lane}: docs routing has selected tests')
            require_job(f'{kind}-test-{runner_class}', 'success' if selected else 'skipped')
            for row in rows:
                artifact = f'{kind}-results-{runner_class}-{row["label"]}'
                if kind == 'smoke':
                    path = artifacts / artifact / 'smoke-results.txt'
                    expected_files.add(path)
                    try:
                        records = {}
                        for line in path.read_text().splitlines():
                            status, separator, script = line.partition(': ')
                            if not separator or status not in ('PASSED', 'SKIPPED', 'FAILED') or script in records:
                                raise ValueError('Invalid or duplicate smoke result')
                            records[script] = status
                        if set(records) != set(row['scripts'].split()):
                            raise ValueError('Missing or unexpected smoke results')
                        errors.extend(f'{artifact}: FAILED {name}' for name, status in records.items() if status == 'FAILED')
                    except (OSError, ValueError) as exc:
                        errors.append(f'{path}: {exc}')
                    continue
                results = read(artifact, 'results.xml')
                represented = {nodeid.split('::')[0] for nodeid in results}
                if represented != set(row['files'].split()):
                    errors.append(f'{artifact}: missing or unexpected integration test files')
                failed = {nodeid for nodeid, status in results.items() if status == 'failed'}
                initial_failures.update((artifact, nodeid) for nodeid in failed)
                exit_path = artifacts / artifact / 'exit-code.txt'
                expected_files.add(exit_path)
                try:
                    code = int(exit_path.read_text().strip())
                    if code != (1 if failed else 0):
                        raise ValueError(f'pytest exit {code} does not match report; only test failures can recover')
                except (OSError, ValueError) as exc:
                    errors.append(f'{exit_path}: {exc}')

    for filename in ('backend-process-results.xml', 'backend-docker-results.xml'):
        results = read('backend-integration-results-linux', filename)
        errors.extend(f'{filename}: FAILED {nodeid}' for nodeid, status in results.items() if status == 'failed')

    outputs = needs.get('collect-integration-rechecks', {}).get('outputs', {})
    rechecks = json.loads(outputs['matrix'])['include']
    # Recompute from the original reports: a collector omission or tampered lane
    # cannot erase an initial failure or retry a passing test.
    recomputed = collect_failed_rechecks(artifacts, routing=routing)
    if rechecks != recomputed:
        errors.append('Recheck matrix does not match original failures and runner metadata')
    if outputs.get('has_rechecks') != str(bool(rechecks)).lower():
        errors.append('Recheck matrix and selection flag disagree')
    require_job('integration-flake-recheck', 'success' if rechecks else 'skipped')
    recovered = set()
    for index, row in enumerate(rechecks):
        source = row['source_artifact']
        nodeid = row['nodeid']
        results = read(f'integration-recheck-results-{source}-{index}', 'recheck-results.xml')
        if results == {nodeid: 'passed'}:
            recovered.add((source, nodeid))
        else:
            errors.append(f'{source}: recheck did not pass exactly the requested testcase {nodeid}')
    for source, nodeid in sorted(initial_failures):
        label = 'FLAKY RECOVERED' if (source, nodeid) in recovered else 'FAILED'
        print(f'{label} {nodeid} [{source}] (initial failure retained)')
        if (source, nodeid) not in recovered:
            errors.append(f'{source}: persistent integration failure {nodeid}')

    actual_files = {path for path in artifacts.glob('*-results-*/*') if path.is_file()}
    for path in sorted(actual_files - expected_files):
        errors.append(f'Unexpected result artifact file: {path}')
    print(f'Checked {len(expected_files)} expected artifact files; {len(initial_failures)} initial failures; '
          f'{len(recovered)} recovered by one recheck')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts_dir', type=Path)
    args = parser.parse_args()
    try:
        errors = summarize(args.artifacts_dir, json.loads(os.environ['CI_NEEDS_JSON']))
    except (KeyError, TypeError, ValueError, OSError, ET.ParseError) as exc:
        errors = [f'Invalid or missing CI evidence: {exc}']
    for error in errors:
        print(f'FAIL: {error}')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
