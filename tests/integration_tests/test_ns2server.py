"""Integration test for ns2server."""

import configparser
import json
import os
import sys
import time

from tests.smoke_tests.ns2_workshop import assert_map_origin, read_map_origins, change_map

import pytest

from conftest import (
    _runtime_probe_hosts,
    workshop_runtime_backends,
    alphagsm_env,
    capture_alphagsm_stop,
    default_runtime_backend,
    effective_runtime_backend,
    resolve_steamcmd_linux_runtime_image,
    run_alphagsm,
    pick_free_tcp_port_group,
    require_command_for_runtime,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_and_assert_ok,
    wait_for_info_protocol,
    wait_for_udp_closed,
    write_config,
)
pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_ns2server_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    module_name = "ns2server"
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itns2server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-NS2-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(2)
    query_port = port + 1

    run_and_assert_ok(
        env,
        server_name,
        "create",
        module_name,
        allow_known_steamcmd_skip=False,
    )

    run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        allow_known_steamcmd_skip=False,
    )

    assert (install_dir / server_name).is_dir()
    assert (install_dir / server_name / "Workshop").is_dir()
    assert (install_dir / "logs").is_dir()
    assert (install_dir / "x64" / "server_linux").exists()

    run_and_assert_ok(
        env,
        server_name,
        "start",
        allow_known_steamcmd_skip=False,
    )

    try:
        wait_for_info_protocol(
            env,
            server_name,
            "a2s",
            START_TIMEOUT,
            expected_port=query_port,
        )

        run_and_assert_ok(
            env,
            server_name,
            "status",
            allow_known_steamcmd_skip=False,
        )

        query_result = run_and_assert_ok(
            env,
            server_name,
            "query",
            allow_known_steamcmd_skip=False,
        )
        assert "Server is responding" in query_result.stdout

        info_result = run_and_assert_ok(
            env,
            server_name,
            "info",
            allow_known_steamcmd_skip=False,
        )
        assert "Protocol" in info_result.stdout

        info_json_result = run_and_assert_ok(
            env,
            server_name,
            "info",
            "--json",
            allow_known_steamcmd_skip=False,
        )
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", info_data
        assert info_data["port"] == query_port, info_data
    finally:
        stop_result = capture_alphagsm_stop(
            env,
            server_name,
            sys.exc_info()[1],
        )

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)


def _run_ns2_workshop_lifecycle(tmp_path, workshop_source, workshop_identifier, runtime_backend):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    module_name = "ns2server"
    runtime_backend = runtime_backend or os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = f"workshop-ns2-{runtime_backend}" if workshop_source else "itns2server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-NS2-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    if workshop_source:
        steamcmd_path = os.environ.get('ALPHAGSM_NS2SERVER_STEAMCMD_PATH', str(tmp_path / 'steamcmd'))
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(config_path, encoding='utf-8')
        if not parser.has_section('downloader.steamcmd'):
            parser.add_section('downloader.steamcmd')
        parser.set('downloader.steamcmd', 'steamcmd_path', steamcmd_path)
        with config_path.open('w', encoding='utf-8') as handle:
            parser.write(handle)
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(4)
    query_port = port + 1

    run_and_assert_ok(
        env,
        server_name,
        "create",
        module_name,
        allow_known_steamcmd_skip=False,
    )

    run_and_assert_ok(env, server_name, 'set', 'httpport', str(port + 2))
    run_and_assert_ok(env, server_name, 'set', 'modserverport', str(port + 3))

    run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        allow_known_steamcmd_skip=False,
    )

    assert (install_dir / server_name).is_dir()
    assert (install_dir / server_name / "Workshop").is_dir()
    assert (install_dir / "logs").is_dir()
    assert (install_dir / "x64" / "server_linux").exists()

    item_ids = []
    if effective_runtime_backend(runtime_backend, module_name=module_name) == 'docker':
        run_and_assert_ok(env, server_name, 'set', 'image', resolve_steamcmd_linux_runtime_image())
        # Docker publishes the container interface, not its private loopback listener.
        run_and_assert_ok(env, server_name, 'set', 'webdomain', '0.0.0.0')
    if workshop_source:
        run_and_assert_ok(env, server_name, 'mod', 'add', workshop_source, workshop_identifier)
        run_and_assert_ok(env, server_name, 'mod', 'apply')
        data = json.loads((home_dir / 'conf' / f'{server_name}.json').read_text())
        item_ids = [entry['workshop_id'] for entry in data['mods']['desired']['workshop']]
        assert item_ids
        cycle = install_dir / server_name / 'MapCycle.json'
        operator = json.loads(cycle.read_text()); operator['alphagsm_test_operator'] = 'preserve'
        cycle.write_text(json.dumps(operator, indent=2))
        run_and_assert_ok(env, server_name, 'set', 'modserveraddress', '127.0.0.1')

    try:
        run_and_assert_ok(
            env,
            server_name,
            "start",
            allow_known_steamcmd_skip=False,
        )
        wait_for_info_protocol(
            env,
            server_name,
            "a2s",
            START_TIMEOUT,
            expected_port=query_port,
        )

        if item_ids:
            _verify_workshop_execution(env, server_name, item_ids, query_port, port + 2,
                                       host=_workshop_admin_host(runtime_backend))

        run_and_assert_ok(
            env,
            server_name,
            "status",
            allow_known_steamcmd_skip=False,
        )

        query_result = run_and_assert_ok(
            env,
            server_name,
            "query",
            allow_known_steamcmd_skip=False,
        )
        assert "Server is responding" in query_result.stdout

        info_result = run_and_assert_ok(
            env,
            server_name,
            "info",
            allow_known_steamcmd_skip=False,
        )
        assert "Protocol" in info_result.stdout

        info_json_result = run_and_assert_ok(
            env,
            server_name,
            "info",
            "--json",
            allow_known_steamcmd_skip=False,
        )
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", info_data
        assert info_data["port"] == query_port, info_data
    finally:
        stop_result = capture_alphagsm_stop(
            env,
            server_name,
            sys.exc_info()[1],
        )

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)

    if item_ids:
        run_and_assert_ok(env, server_name, 'mod', 'cleanup')
        remaining = json.loads(cycle.read_text())
        assert remaining['alphagsm_test_operator'] == 'preserve'
        assert not set(format(int(item), 'x') for item in item_ids).intersection(remaining.get('mods', []))


@pytest.mark.skipif(os.environ.get('ALPHAGSM_RUN_NS2SERVER_WORKSHOP') != '1',
                    reason='Opt in to external native NS2 Workshop lifecycle validation')
@pytest.mark.parametrize('runtime_backend', workshop_runtime_backends())
def test_ns2server_workshop_loads(tmp_path, runtime_backend):
    identifier = os.environ.get('ALPHAGSM_NS2SERVER_WORKSHOP_COLLECTION')
    source = 'workshop-collection' if identifier else 'workshop'
    identifier = identifier or os.environ.get('ALPHAGSM_NS2SERVER_WORKSHOP_ITEM', '129599221')
    _run_ns2_workshop_lifecycle(tmp_path, source, identifier, runtime_backend)


def _workshop_admin_host(runtime_backend):
    """Use the published sibling endpoint when pytest runs in a manager container."""
    if effective_runtime_backend(runtime_backend, module_name='ns2server') == 'docker':
        return _runtime_probe_hosts('127.0.0.1')[-1]
    return '127.0.0.1'


def _verify_workshop_execution(env, server_name, item_ids, query_port, http_port, *, host):
    """Require actual custom map execution and native engine attribution to its mod."""
    item = os.environ.get('ALPHAGSM_NS2SERVER_WORKSHOP_LOAD_ITEM', item_ids[0])
    map_name = os.environ.get('ALPHAGSM_NS2SERVER_WORKSHOP_MAP', 'ns2_jambi')
    assert item in item_ids and map_name and all(char.isalnum() or char in '_-' for char in map_name)
    deadline, error, selected = time.monotonic() + 300, None, False
    while time.monotonic() < deadline:
        try:
            origins = read_map_origins(host, http_port, 'admin', 'CHANGE_ME')
            assert_map_origin(origins, map_name, item)
            if not selected:
                change_map(host, http_port, 'admin', 'CHANGE_ME', map_name)
                selected = True
        except (ValueError, OSError, AssertionError) as exc:
            error = exc
        result = run_alphagsm(env, server_name, 'info', '--json')
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout.strip())
                if data.get('protocol') == 'a2s' and data.get('port') == query_port and data.get('map', '').lower() == map_name.lower():
                    origins = read_map_origins(host, http_port, 'admin', 'CHANGE_ME')
                    assert_map_origin(origins, map_name, item)
                    print(f'ENGINE_WORKSHOP_MAP_LOADED {map_name} app=4920 item={item} native_map_origin={origins}')
                    return
            except (ValueError, OSError, AssertionError) as exc:
                error = exc
        time.sleep(2)
    output = run_and_assert_ok(env, server_name, 'logs', '-n', '20000').stdout
    pytest.fail(f'NS2 engine did not execute Workshop map {map_name} from {item}: {error}\n{output[-20000:]}')
