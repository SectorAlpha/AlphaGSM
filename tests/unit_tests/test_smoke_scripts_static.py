"""Static contract tests for smoke runners that should follow declared runtimes."""

from pathlib import Path


LIFE_IS_FEUDAL_SMOKE = Path("tests/smoke_tests/run_lifeisfeudalserver.sh")
PALWORLD_SMOKE = Path("tests/smoke_tests/run_palworld.sh")
SCUM_SMOKE = Path("tests/smoke_tests/run_scumserver.sh")
SS14_SMOKE = Path("tests/smoke_tests/run_ss14server.sh")
NIGHTINGALE_SMOKE = Path("tests/smoke_tests/run_nightingale.sh")
MYTH_OF_EMPIRES_SMOKE = Path("tests/smoke_tests/run_mythofempiresserver.sh")
BLACK_OPS_3_SMOKE = Path("tests/smoke_tests/run_blackops3server.sh")
SNIPER_ELITE_4_SMOKE = Path("tests/smoke_tests/run_sniperelite4server.sh")
COD_SERVER_SMOKE = Path("tests/smoke_tests/run_codserver.sh")
CONAN_EXILES_SMOKE = Path("tests/smoke_tests/run_conanexiles.sh")
RETURN_TO_MORIA_SMOKE = Path("tests/smoke_tests/run_returntomoriaserver.sh")
ASA_SMOKE = Path("tests/smoke_tests/run_arksurvivalascended.sh")
ASTRONEER_SMOKE = Path("tests/smoke_tests/run_astroneerserver.sh")
STEAMCMD_HELPERS = Path("tests/smoke_tests/steamcmd_helpers.sh")
WORKFLOW = Path(".github/workflows/unittest.yaml")


def test_life_is_feudal_smoke_uses_docker_runtime_backend():
    text = LIFE_IS_FEUDAL_SMOKE.read_text(encoding="utf-8")

    assert "[runtime]" in text
    assert "backend = docker" in text
    assert "image_wine_proton = $IMAGE" in text


def test_life_is_feudal_smoke_resolves_wine_proton_image_instead_of_screen():
    text = LIFE_IS_FEUDAL_SMOKE.read_text(encoding="utf-8")

    assert 'ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON' in text
    assert 'run_alphagsm "$SERVER_NAME" set image "$IMAGE"' in text
    assert 'require_cmd screen' not in text


def test_scum_smoke_uses_shared_work_root_and_start_retry_contract():
    text = SCUM_SMOKE.read_text(encoding="utf-8")

    assert 'WORK_ROOT="$(resolve_work_root)"' in text
    assert 'WORK_DIR="$(mktemp -d -p "$WORK_ROOT" scumserver-smoke.XXXXXX)"' in text
    assert 'run_start_with_port_retry "$SERVER_NAME"' in text
    assert 'run_alphagsm "$SERVER_NAME" start' not in text


def test_palworld_smoke_uses_shared_start_retry_contract():
    text = PALWORLD_SMOKE.read_text(encoding="utf-8")

    assert 'run_start_with_port_retry "$SERVER_NAME"' in text
    assert 'run_alphagsm "$SERVER_NAME" start' not in text


def test_ss14_smoke_supports_byo_archive_url_and_standard_prerequisite_skip():
    text = SS14_SMOKE.read_text(encoding="utf-8")

    assert "ENABLED (BYO)" in text
    assert "ALPHAGSM_SS14_SERVER_URL" in text
    assert 'run_setup_or_skip_steamcmd "${setup_args[@]}"' in text


def test_nightingale_smoke_uses_official_http_status_surface():
    text = NIGHTINGALE_SMOKE.read_text(encoding="utf-8")

    assert 'PORT="$(pick_free_port_group 2)"' in text
    assert 'wait_for_info_protocol "$SERVER_NAME" "http_status"' in text
    assert 'wait_for_info_protocol "$SERVER_NAME" "tcp"' not in text


def test_nightingale_smoke_allows_slow_first_world_bootstrap_and_captures_logs():
    text = NIGHTINGALE_SMOKE.read_text(encoding="utf-8")

    assert 'START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-600}"' in text
    assert 'capture_application_logs "$INSTALL_DIR"/NWX/Saved/Logs/*.log' in text
    assert 'capture_runtime_diagnostics "$SERVER_NAME"' in text


def test_myth_of_empires_smoke_uses_docker_runtime_and_a2s_info():
    text = MYTH_OF_EMPIRES_SMOKE.read_text(encoding="utf-8")

    assert "backend = docker" in text
    assert "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON" in text
    assert 'run_alphagsm "$SERVER_NAME" set image "$DOCKER_IMAGE"' in text
    assert 'wait_for_info_protocol "$SERVER_NAME" "a2s"' in text
    assert "require_proton" not in text
    assert "require_cmd screen" not in text


def test_black_ops_3_smoke_is_active_on_docker_udp_health_surface():
    text = BLACK_OPS_3_SMOKE.read_text(encoding="utf-8")

    assert "Smoke test for blackops3server is disabled" not in text
    assert "backend = docker" in text
    assert "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON" in text
    assert 'PORT="$(pick_free_port_group 3)"' in text
    assert "CreateDedicatedModsLobby: ready!" in text
    assert 'wait_for_info_protocol "$SERVER_NAME" "udp"' in text


def test_sniper_elite_4_smoke_captures_exited_container_diagnostics():
    text = SNIPER_ELITE_4_SMOKE.read_text(encoding="utf-8")
    helpers = STEAMCMD_HELPERS.read_text(encoding="utf-8")

    diagnostics_call = 'capture_container_process_diagnostics "$SERVER_NAME"'

    assert "capture_container_process_diagnostics()" in helpers
    assert "ExitCode: {{.State.ExitCode}}" in helpers
    assert diagnostics_call in text


def test_codserver_smoke_skips_before_start_when_byo_map_content_is_missing():
    text = COD_SERVER_SMOKE.read_text(encoding="utf-8")

    map_check = "from gamemodules.codserver import has_start_map"
    assert map_check in text
    assert '"mp_carentan"' in text
    assert "exit 77" in text
    assert text.index(map_check) < text.index('run_alphagsm "$SERVER_NAME" start')


def test_conan_exiles_smoke_uses_native_linux_runtime_and_reserves_pinger_port():
    text = CONAN_EXILES_SMOKE.read_text(encoding="utf-8")

    assert "ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX" in text
    assert "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON" not in text
    assert 'PORT="$(pick_free_port_group 2)"' in text
    assert "backend = docker" in text


def test_return_to_moria_smoke_supports_current_and_legacy_status_paths():
    text = RETURN_TO_MORIA_SMOKE.read_text(encoding="utf-8")

    assert '"$INSTALL_DIR/Moria/Config/Status.json"' in text
    assert '"$INSTALL_DIR/Moria/Config/status.json"' in text
    assert '"$INSTALL_DIR/Moria/Saved/Config/Status.json"' in text
    assert '"$INSTALL_DIR/Moria/Saved/Config/status.json"' in text
    assert 'STATUS_JSON_CANDIDATES=(' in text


def test_return_to_moria_smoke_wakes_the_enabled_console_after_start():
    text = RETURN_TO_MORIA_SMOKE.read_text(encoding="utf-8")

    start = 'run_alphagsm "$SERVER_NAME" start'
    wake = 'run_alphagsm "$SERVER_NAME" send " "'
    assert start in text
    assert wake in text
    assert text.index(start) < text.index(wake)


def test_asa_smoke_uses_udp_game_pair_and_authenticated_rcon():
    text = ASA_SMOKE.read_text(encoding="utf-8")

    assert "backend = docker" in text
    assert 'PORT="$(pick_free_port)"' in text
    assert 'RCONPORT="$(pick_free_port)"' in text
    assert 'while [[ "$RCONPORT" -eq "$PORT" ]]' in text
    set_queryport = 'run_alphagsm "$SERVER_NAME" set rconport "$RCONPORT"'
    setup = 'run_setup_or_skip_steamcmd "$SERVER_NAME" setup'
    assert set_queryport in text
    assert text.index(set_queryport) < text.index(setup)
    assert 'wait_for_info_protocol "$SERVER_NAME" "source_rcon"' in text
    assert 'wait_for_info_protocol "$SERVER_NAME" "tcp"' not in text


def test_astroneer_smoke_requires_network_log_before_udp_info():
    text = ASTRONEER_SMOKE.read_text(encoding="utf-8")

    glob_ready = 'wait_for_glob_ready_strict "$INSTALL_DIR/Astro/Saved/Logs/*.log"'
    udp_ready = 'wait_for_info_protocol "$SERVER_NAME" "udp"'
    assert "backend = docker" in text
    assert glob_ready in text
    assert '"IpNetDriver listening on port $PORT"' in text
    assert "GameNetDriver" not in text
    assert udp_ready in text
    assert text.index(glob_ready) < text.index(udp_ready)
    assert 'wait_for_info_protocol "$SERVER_NAME" tcp' not in text
    assert 'wait_for_info_protocol "$SERVER_NAME" "tcp"' not in text


def test_astroneer_smoke_captures_container_diagnostics_before_cleanup():
    text = ASTRONEER_SMOKE.read_text(encoding="utf-8")
    helpers = STEAMCMD_HELPERS.read_text(encoding="utf-8")

    readiness_call = (
        'wait_for_glob_ready_strict "$INSTALL_DIR/Astro/Saved/Logs/*.log"'
    )
    diagnostics_call = 'capture_runtime_diagnostics "$SERVER_NAME"'

    assert "capture_runtime_diagnostics()" in helpers
    assert 'run_alphagsm "$server_name" doctor' in helpers
    assert 'run_alphagsm "$server_name" logs -n 200' in helpers
    assert diagnostics_call in text
    assert text.index(readiness_call) < text.index(diagnostics_call)


def test_astroneer_smoke_captures_process_and_engine_config_before_cleanup():
    text = ASTRONEER_SMOKE.read_text(encoding="utf-8")
    helpers = STEAMCMD_HELPERS.read_text(encoding="utf-8")

    diagnostics_call = 'capture_container_process_diagnostics "$SERVER_NAME"'
    engine_config = '"$INSTALL_DIR/Astro/Saved/Config/WindowsServer/Engine.ini"'
    server_settings = (
        '"$INSTALL_DIR/Astro/Saved/Config/WindowsServer/AstroServerSettings.ini"'
    )

    assert "capture_container_process_diagnostics()" in helpers
    assert "ExitCode: {{.State.ExitCode}}" in helpers
    assert 'docker exec "$container_name" ps -eo pid,ppid,stat,comm,args' in helpers
    assert "ALPHAGSM_PREFER_PROTON" in helpers
    assert diagnostics_call in text
    assert engine_config in text
    assert server_settings in text


def test_astroneer_smoke_records_registration_settings_before_start():
    text = ASTRONEER_SMOKE.read_text(encoding="utf-8")

    setup_call = 'run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"'
    registration_diagnostic = (
        'capture_astroneer_registration_diagnostics '
        '"$INSTALL_DIR/Astro/Saved/Config/WindowsServer/AstroServerSettings.ini"'
    )
    start_call = 'run_alphagsm "$SERVER_NAME" start'

    assert "capture_astroneer_registration_diagnostics()" in text
    assert registration_diagnostic in text
    assert text.index(setup_call) < text.index(registration_diagnostic)
    assert text.index(registration_diagnostic) < text.index(start_call)


def test_astroneer_smoke_sets_managed_registration_ip_before_setup():
    text = ASTRONEER_SMOKE.read_text(encoding="utf-8")

    set_registration_ip = (
        'run_alphagsm "$SERVER_NAME" set registration_publicip '
        '"$ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP"'
    )
    setup_call = 'run_setup_or_skip_steamcmd "$SERVER_NAME" setup -n "$PORT" "$INSTALL_DIR"'

    assert "ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP" in text
    assert set_registration_ip in text
    assert text.index(set_registration_ip) < text.index(setup_call)


def test_astroneer_smoke_reports_missing_external_endpoint_as_explicit_skip():
    text = ASTRONEER_SMOKE.read_text(encoding="utf-8")

    assert "SKIPPED: Astroneer smoke requires" in text
    assert "exit 77" in text


def test_workflow_reports_smoke_skips_separately_from_passes_and_failures():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert text.count('echo "SKIPPED: $script" | tee -a smoke-results.txt') == 2
    assert text.count('if [ "$rc" -eq 77 ]; then') == 2
    assert "scripts/summarize_tests.py artifacts" in text
    summary = Path("scripts/summarize_tests.py").read_text(encoding="utf-8")
    assert "('PASSED', 'SKIPPED', 'FAILED')" in summary


def test_strict_glob_readiness_alias_reuses_required_helper():
    text = STEAMCMD_HELPERS.read_text(encoding="utf-8")

    assert "wait_for_glob_ready_strict()" in text
    assert 'wait_for_glob_ready "$log_glob" "$timeout_seconds" "$pattern" "required"' in text
    assert "readiness_mode" not in text
    assert "return 1" in text
