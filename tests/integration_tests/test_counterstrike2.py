"""Integration test for counterstrike2."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

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
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    wait_for_info_protocol,
    set_source_hibernation,
    assert_source_server_empty,
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


def _prepare_empty_competitive_server(install_dir):
    """Configure this disposable fixture after Valve's competitive defaults."""
    config_dir = Path(install_dir) / 'game/csgo/cfg'
    server_cfg = config_dir / 'server.cfg'
    assert server_cfg.is_file(), f'CS2 native server config missing: {server_cfg}'
    override = config_dir / 'gamemode_competitive_server.cfg'
    assert not (override.exists() or override.is_symlink()), f'Unexpected existing CS2 test override: {override}'
    set_source_hibernation(server_cfg, enabled=False)
    override.write_text('bot_quota 0\nbot_kick\nsv_hibernate_when_empty 0\n', encoding='utf-8')


def _assert_empty_cs2_info(data, port):
    """Require the actual managed A2S endpoint and expected empty native map."""
    assert data.get('protocol') == 'a2s', data
    assert data.get('port') == port, data
    assert data.get('map') == 'de_dust2', data
    assert data.get('bots') == 0, data
    assert_source_server_empty(data)


@pytest.mark.timeout(SETUP_TIMEOUT + 2 * START_TIMEOUT + STOP_TIMEOUT + 600)
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

    _prepare_empty_competitive_server(install_dir)

    run_and_assert_ok(env, server_name, "start")

    try:
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        run_and_assert_ok(env, server_name, "status")

        # Native A2S, followed by the CLI's structured A2S result, proves
        # readiness without depending on Source1 console strings or flush timing.
        wait_for_a2s_ready(query_host, port, START_TIMEOUT, log_path=log_path)
        awake_info = wait_for_info_protocol(
            env, server_name, "a2s", START_TIMEOUT, expected_port=port)
        _assert_empty_cs2_info(awake_info, port)

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
        _assert_empty_cs2_info(_info_data, port)
    finally:
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT)

    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
    final_status = run_and_assert_ok(env, server_name, 'status')
    assert "isn't running" in final_status.stdout
