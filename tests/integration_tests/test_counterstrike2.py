"""Integration test for counterstrike2."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    default_runtime_backend,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_info_protocol,
    read_info_json,
    find_source_server_cfg,
    set_source_hibernation,
    assert_source_server_empty,
    wait_for_runtime_log_marker,
    wait_for_a2s_ready,
    wait_for_udp_closed,
)
from gamemodules.counterstrike2 import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
# Run 38775144746 installed the 73.4 GB depot in 1340s, longer than the
# former 900s initial limit plus its 240s retry allowance combined.
SETUP_TIMEOUT = 3600


def _log_setup_download_diagnostics(env, install_dir):
    """Retain bounded native progress without reading Steam account state."""
    install_dir = Path(install_dir)
    home = Path(env.get('HOME') or Path.home())
    roots = [home / 'Steam', home / '.local/share/Steam']
    if env.get('ALPHAGSM_WORK_DIR'):
        roots.insert(0, Path(env['ALPHAGSM_WORK_DIR']) / 'steamcmd')
    payload = {'steam_logs': [], 'app_manifests': []}
    try:
        disk = shutil.disk_usage(install_dir.parent)
        payload['disk'] = {'total_bytes': disk.total, 'free_bytes': disk.free}
    except OSError as exc:
        payload['disk'] = {'error': str(exc)}
    for root in roots:
        path = root / 'logs/content_log.txt'
        try:
            with path.open('rb') as handle:
                handle.seek(0, os.SEEK_END)
                handle.seek(max(0, handle.tell() - 8192))
                text = handle.read(8192).decode('utf-8', errors='replace')
            payload['steam_logs'].append({'path': str(path), 'tail': '\n'.join(text.splitlines()[-30:])})
        except OSError:
            continue
    for root in [install_dir, *roots]:
        path = root / f'steamapps/appmanifest_{steam_app_id}.acf'
        try:
            with path.open('rb') as handle:
                text = handle.read(16384).decode('utf-8', errors='replace')
        except OSError:
            continue
        # Counters and result flags explain download, staging or disk failures;
        # do not dump manifests' arbitrary strings or Steam's credential files.
        counters = dict(re.findall(
            r'"(StateFlags|UpdateResult|SizeOnDisk|BytesToDownload|BytesDownloaded|BytesToStage|BytesStaged)"\s+"([0-9]{1,20})"', text))
        payload['app_manifests'].append({'path': str(path), 'counters': counters})
    log_command_result('CS2 SteamCMD download diagnostics', subprocess.CompletedProcess(
        ['CS2 SteamCMD download diagnostics'], 0, json.dumps(payload), ''))


def _run_setup(env, server_name, port, install_dir):
    """Give the full CS2 depot one bounded attempt; timeouts remain failures."""
    args = (server_name, "setup", "-n", str(port), str(install_dir))
    try:
        result = run_alphagsm(env, *args, timeout=SETUP_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout.decode(errors='replace') if isinstance(exc.stdout, bytes) else exc.stdout or ''
        error = exc.stderr.decode(errors='replace') if isinstance(exc.stderr, bytes) else exc.stderr or ''
        log_command_result(
            "alphagsm " + " ".join(args) + " [timed out]",
            subprocess.CompletedProcess(exc.cmd, 124, output,
                                        f'Timed out after {SETUP_TIMEOUT}s\n' + error),
        )
        _log_setup_download_diagnostics(env, install_dir)
        pytest.fail(f'Counter-Strike 2 setup exceeded {SETUP_TIMEOUT}s; '
                    'see captured SteamCMD output and native download diagnostics')

    log_command_result("alphagsm " + " ".join(args), result)
    if result.returncode != 0:
        _log_setup_download_diagnostics(env, install_dir)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


@pytest.mark.timeout(SETUP_TIMEOUT + 3 * START_TIMEOUT + STOP_TIMEOUT + 600)
def test_counterstrike2_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "counterstrike2"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itcounterstrike2"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    query_host = detect_query_host()

    run_and_assert_ok(env, server_name, "create", module_name)

    _run_setup(env, server_name, port, install_dir)

    server_cfg_path = find_source_server_cfg(install_dir)
    set_source_hibernation(server_cfg_path, enabled=False)

    run_and_assert_ok(env, server_name, "start")

    try:
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["SV_ActivateServer", "VAC secure mode"],
            START_TIMEOUT,
        )

        run_and_assert_ok(env, server_name, "status")

        wait_for_a2s_ready(query_host, port, 600, log_path=log_path)
        awake_info = wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)
        assert_source_server_empty(awake_info)

        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players     : 0/" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert_source_server_empty(_info_data)
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
