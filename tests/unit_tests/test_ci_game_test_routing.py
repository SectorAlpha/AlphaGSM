"""Static checks for PR routing of Linux game smoke and integration tests."""

from pathlib import Path

import pytest

from tests.helpers import load_module_from_repo


WORKFLOW_PATH = Path(".github/workflows/unittest.yaml")
ROUTING_SCRIPT = Path("scripts/ci_game_test_routing.py")


def load_routing_module():
    assert ROUTING_SCRIPT.exists(), f"missing routing helper: {ROUTING_SCRIPT}"
    return load_module_from_repo("ci_game_test_routing_static", str(ROUTING_SCRIPT))


def test_docs_only_changes_skip_linux_game_smoke_and_integration():
    routing = load_routing_module()

    result = routing.classify_changed_files(
        [
            "docs/docker-manager.md",
            "skills/server-lifecycle/SKILL.md",
            "README.md",
            "docker/README.md",
        ],
        repo_root=Path("."),
    )

    assert result["mode"] == "skip"
    assert result["smoke_scripts"] == []
    assert result["integration_tests"] == []


def test_module_only_changes_target_matching_linux_game_tests():
    routing = load_routing_module()

    result = routing.classify_changed_files(
        ["src/gamemodules/counterstrike2.py"],
        repo_root=Path("."),
    )

    assert result["mode"] == "targeted"
    assert result["smoke_scripts"] == ["tests/smoke_tests/run_counterstrike2.sh"]
    assert result["integration_tests"] == [
        "tests/integration_tests/test_counterstrike2.py"
    ]


def test_routing_outputs_split_heavy_and_standard_game_matrices():
    routing = load_routing_module()

    outputs = routing.build_outputs_for_changed_files(
        [
            "src/gamemodules/palworld/main.py",
            "src/gamemodules/counterstrike2.py",
        ],
        repo_root=Path("."),
    )

    assert outputs["has_smoke_standard_tests"] == "true"
    assert outputs["has_smoke_heavy_tests"] == "true"
    assert outputs["has_integration_standard_tests"] == "true"
    assert outputs["has_integration_heavy_tests"] == "true"
    assert "run_counterstrike2.sh" in outputs["smoke_standard_matrix"]
    assert "run_palworld.sh" in outputs["smoke_heavy_matrix"]
    assert "test_counterstrike2.py" in outputs["integration_standard_matrix"]
    assert "test_palworld.py" in outputs["integration_heavy_matrix"]


def test_long_container_integration_changes_route_to_heavy_matrix():
    routing = load_routing_module()

    outputs = routing.build_outputs_for_changed_files(
        [
            "src/gamemodules/sniperelite4server/main.py",
            "src/gamemodules/sonsoftheforestserver/main.py",
        ],
        repo_root=Path("."),
    )

    assert outputs["has_integration_standard_tests"] == "false"
    assert outputs["has_integration_heavy_tests"] == "true"
    assert "test_sniperelite4server.py" in outputs["integration_heavy_matrix"]
    assert "test_sonsoftheforestserver.py" in outputs["integration_heavy_matrix"]


def test_source_family_backlog_no_longer_contains_tf2_or_counterstrike2():
    routing = load_routing_module()

    backlog = routing.docker_enablement_backlog_tests(repo_root=Path("."))

    assert "tests/integration_tests/test_tf2.py" not in backlog
    assert "tests/integration_tests/test_counterstrike2.py" not in backlog


def test_source_shared_batch_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_cssserver.py",
        "tests/integration_tests/test_dodsserver.py",
        "tests/integration_tests/test_hl2dmserver.py",
        "tests/integration_tests/test_nmrihserver.py",
    ):
        assert test_path not in backlog


def test_goldsrc_batch_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_ahlserver.py",
        "tests/integration_tests/test_bdserver.py",
        "tests/integration_tests/test_csserver.py",
        "tests/integration_tests/test_csczserver.py",
        "tests/integration_tests/test_dmcserver.py",
        "tests/integration_tests/test_dodserver.py",
        "tests/integration_tests/test_hldmserver.py",
    ):
        assert test_path not in backlog


def test_hldmsserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_hldmsserver.py" not in backlog


def test_l4dserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_l4dserver.py" not in backlog


def test_counterstrike2_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_counterstrike2.py" not in backlog


def test_counterstrikeglobaloffensive_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_counterstrikeglobaloffensive.py" not in backlog


def test_aloftserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_aloftserver.py" not in backlog


def test_goldeneyesourceserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_goldeneyesourceserver.py" not in backlog


def test_emserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_emserver.py" not in backlog


def test_groundbranch_hurtworld_hz_icarus_ios_jc2_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_groundbranchserver.py",
        "tests/integration_tests/test_hurtworldserver.py",
        "tests/integration_tests/test_hzserver.py",
        "tests/integration_tests/test_icarusserver.py",
        "tests/integration_tests/test_iosserver.py",
        "tests/integration_tests/test_jc2server.py",
    ):
        assert test_path not in backlog


def test_jc3_kerbal_lastoasis_longvinter_medievalengineers_minecraft_bedrock_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_jc3server.py",
        "tests/integration_tests/test_kerbalspaceprogramserver.py",
        "tests/integration_tests/test_lastoasisserver.py",
        "tests/integration_tests/test_longvinterserver.py",
        "tests/integration_tests/test_medievalengineersserver.py",
        "tests/integration_tests/test_minecraft_bedrock.py",
    ):
        assert test_path not in backlog


def test_miscreated_mohaa_mta_nightingale_noonesurvived_notd_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_miscreatedserver.py",
        "tests/integration_tests/test_mohaaserver.py",
        "tests/integration_tests/test_mtaserver.py",
        "tests/integration_tests/test_nightingale.py",
        "tests/integration_tests/test_noonesurvivedserver.py",
        "tests/integration_tests/test_notdserver.py",
    ):
        assert test_path not in backlog


def test_ohd_palworld_pvr_readyornot_rs2_rw_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_ohdserver.py",
        "tests/integration_tests/test_palworld.py",
        "tests/integration_tests/test_pvrserver.py",
        "tests/integration_tests/test_readyornotserver.py",
        "tests/integration_tests/test_rs2server.py",
        "tests/integration_tests/test_rwserver.py",
    ):
        assert test_path not in backlog


def test_scum_seserver_sniperelite4_sof2_sonsoftheforest_soulmask_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_scumserver.py",
        "tests/integration_tests/test_seserver.py",
        "tests/integration_tests/test_sniperelite4server.py",
        "tests/integration_tests/test_sof2server.py",
        "tests/integration_tests/test_sonsoftheforestserver.py",
        "tests/integration_tests/test_soulmask.py",
    ):
        assert test_path not in backlog


def test_starrupture_subnautica_subsistence_terraria_tshock_tiserver_ut3_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_starruptureserver.py",
        "tests/integration_tests/test_subnauticaserver.py",
        "tests/integration_tests/test_subsistenceserver.py",
        "tests/integration_tests/test_terraria_tshock.py",
        "tests/integration_tests/test_tiserver.py",
        "tests/integration_tests/test_ut3server.py",
    ):
        assert test_path not in backlog


def test_dayzserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_dayzserver.py" not in backlog


def test_doiserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_doiserver.py" not in backlog


def test_askaserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_askaserver.py" not in backlog


def test_tf2_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_tf2.py" not in backlog


def test_tf2cserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_tf2cserver.py" not in backlog


def test_ahl2server_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_ahl2server.py" not in backlog


def test_fofserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_fofserver.py" not in backlog


def test_acserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_acserver.py" not in backlog


def test_insserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_insserver.py" not in backlog


def test_svenserver_moves_out_of_source_family_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_backlog_for_family("source-family", repo_root=Path(".")))

    assert "tests/integration_tests/test_svenserver.py" not in backlog


def test_ts3server_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_ts3server.py" not in backlog


def test_accserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_accserver.py" not in backlog


def test_btlserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_btlserver.py" not in backlog


def test_bf1942server_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_bf1942server.py" not in backlog


def test_bobserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_bobserver.py" not in backlog


def test_bf1942server_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_bf1942server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_bf1942server.py",
            "label": "bf1942server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_bf1942server.py",
            "label": "bf1942server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_bmdmserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_bmdmserver.py" not in backlog


def test_bmdmserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_bmdmserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_bmdmserver.py",
            "label": "bmdmserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_bmdmserver.py",
            "label": "bmdmserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_bobserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_bobserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_bobserver.py",
            "label": "bobserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_bobserver.py",
            "label": "bobserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_bobserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_bobserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_ohdserver.py",
        "tests/integration_tests/test_palworld.py",
        "tests/integration_tests/test_pvrserver.py",
        "tests/integration_tests/test_readyornotserver.py",
        "tests/integration_tests/test_rs2server.py",
        "tests/integration_tests/test_rwserver.py",
        "tests/integration_tests/test_starruptureserver.py",
        "tests/integration_tests/test_subnauticaserver.py",
        "tests/integration_tests/test_subsistenceserver.py",
        "tests/integration_tests/test_terraria_tshock.py",
        "tests/integration_tests/test_tiserver.py",
        "tests/integration_tests/test_ut3server.py",
    ],
)
def test_selected_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_abfserver.py",
        "tests/integration_tests/test_accserver.py",
        "tests/integration_tests/test_aloftserver.py",
        "tests/integration_tests/test_arma2coserver.py",
        "tests/integration_tests/test_arma3_altislife.py",
        "tests/integration_tests/test_arma3_desolationredux.py",
        "tests/integration_tests/test_arma3_epoch.py",
        "tests/integration_tests/test_arma3_exile.py",
        "tests/integration_tests/test_arma3_headless.py",
        "tests/integration_tests/test_arma3_vanilla.py",
        "tests/integration_tests/test_arma3_wasteland.py",
        "tests/integration_tests/test_arma3altislifeserver.py",
    ],
)
def test_next_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_arma3desolationreduxserver.py",
        "tests/integration_tests/test_arma3epochserver.py",
        "tests/integration_tests/test_arma3exileserver.py",
        "tests/integration_tests/test_arma3headlessserver.py",
        "tests/integration_tests/test_arma3server.py",
        "tests/integration_tests/test_arma3wastelandserver.py",
        "tests/integration_tests/test_atsserver.py",
        "tests/integration_tests/test_battlebitserver.py",
        "tests/integration_tests/test_battlecryoffreedomserver.py",
        "tests/integration_tests/test_bb2server.py",
        "tests/integration_tests/test_bbserver.py",
        "tests/integration_tests/test_bdserver.py",
    ],
)
def test_follow_on_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_bf1942server.py",
        "tests/integration_tests/test_bobserver.py",
        "tests/integration_tests/test_boserver.py",
        "tests/integration_tests/test_brickadiaserver.py",
        "tests/integration_tests/test_brokeprotocolserver.py",
        "tests/integration_tests/test_btlserver.py",
        "tests/integration_tests/test_ccserver.py",
        "tests/integration_tests/test_chivalryserver.py",
        "tests/integration_tests/test_citadelserver.py",
        "tests/integration_tests/test_ckserver.py",
        "tests/integration_tests/test_cod2server.py",
        "tests/integration_tests/test_cod4server.py",
    ],
)
def test_next_alphabetical_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_codserver.py",
        "tests/integration_tests/test_counterstrike2.py",
        "tests/integration_tests/test_counterstrikeglobaloffensive.py",
        "tests/integration_tests/test_craftopiaserver.py",
        "tests/integration_tests/test_csczserver.py",
        "tests/integration_tests/test_csserver.py",
        "tests/integration_tests/test_dayofdragonsserver.py",
        "tests/integration_tests/test_dayzarma2epochserver.py",
        "tests/integration_tests/test_deadmatterserver.py",
        "tests/integration_tests/test_dmcserver.py",
        "tests/integration_tests/test_dodserver.py",
        "tests/integration_tests/test_dstserver.py",
    ],
)
def test_following_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_scumserver.py",
        "tests/integration_tests/test_seserver.py",
        "tests/integration_tests/test_sniperelite4server.py",
        "tests/integration_tests/test_sof2server.py",
        "tests/integration_tests/test_sonsoftheforestserver.py",
        "tests/integration_tests/test_soulmask.py",
        "tests/integration_tests/test_svenserver.py",
        "tests/integration_tests/test_ut2k4server.py",
        "tests/integration_tests/test_vsserver.py",
        "tests/integration_tests/test_warbandserver.py",
        "tests/integration_tests/test_wurmserver.py",
        "tests/integration_tests/test_zmrserver.py",
    ],
)
def test_latest_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_ducksideserver.py",
        "tests/integration_tests/test_empyrionserver.py",
        "tests/integration_tests/test_exfilserver.py",
        "tests/integration_tests/test_fearthenightserver.py",
        "tests/integration_tests/test_fofserver.py",
        "tests/integration_tests/test_foundryserver.py",
        "tests/integration_tests/test_frozenflameserver.py",
        "tests/integration_tests/test_goldeneyesourceserver.py",
        "tests/integration_tests/test_gtafivemserver.py",
        "tests/integration_tests/test_gravserver.py",
        "tests/integration_tests/test_heatserver.py",
        "tests/integration_tests/test_hcuserver.py",
    ],
)
def test_newest_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_roserver.py",
        "tests/integration_tests/test_ror2server.py",
        "tests/integration_tests/test_rimworldtogetherserver.py",
        "tests/integration_tests/test_ricochetserver.py",
        "tests/integration_tests/test_returntomoriaserver.py",
        "tests/integration_tests/test_remnantsserver.py",
        "tests/integration_tests/test_reignofdwarfserver.py",
        "tests/integration_tests/test_redmserver.py",
        "tests/integration_tests/test_pvkiiserver.py",
        "tests/integration_tests/test_projectzomboid.py",
        "tests/integration_tests/test_primalcarnageextinctionserver.py",
        "tests/integration_tests/test_port_manager_source_collision.py",
    ],
)
def test_followup_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_police1013server.py",
        "tests/integration_tests/test_pcarserver.py",
        "tests/integration_tests/test_pcars2server.py",
        "tests/integration_tests/test_pathoftitansserver.py",
        "tests/integration_tests/test_outpostzeroserver.py",
        "tests/integration_tests/test_onsetserver.py",
        "tests/integration_tests/test_nsserver.py",
        "tests/integration_tests/test_ns2server.py",
        "tests/integration_tests/test_ns2cserver.py",
        "tests/integration_tests/test_ndserver.py",
        "tests/integration_tests/test_mythofempiresserver.py",
        "tests/integration_tests/test_mw3server.py",
    ],
)
def test_next_followup_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_mumbleserver.py",
        "tests/integration_tests/test_motortownserver.py",
        "tests/integration_tests/test_mordserver.py",
        "tests/integration_tests/test_reignofkingsserver.py",
        "tests/integration_tests/test_pixarkserver.py",
        "tests/integration_tests/test_mxbikesserver.py",
        "tests/integration_tests/test_memoriesofmarsserver.py",
        "tests/integration_tests/test_minecraft_bedrock.py",
        "tests/integration_tests/test_insserver.py",
        "tests/integration_tests/test_hogwarpserver.py",
        "tests/integration_tests/test_medievalengineersserver.py",
        "tests/integration_tests/test_longvinterserver.py",
    ],
)
def test_penultimate_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


@pytest.mark.parametrize(
    "test_path",
    [
        "tests/integration_tests/test_ets2server.py",
        "tests/integration_tests/test_lifeisfeudalserver.py",
        "tests/integration_tests/test_lastoasisserver.py",
        "tests/integration_tests/test_l4dserver.py",
        "tests/integration_tests/test_hldmserver.py",
        "tests/integration_tests/test_kfserver.py",
        "tests/integration_tests/test_hldmsserver.py",
        "tests/integration_tests/test_hellletlooseserver.py",
        "tests/integration_tests/test_kf2server.py",
        "tests/integration_tests/test_interstellarriftserver.py",
        "tests/integration_tests/test_jc3server.py",
        "tests/integration_tests/test_kerbalspaceprogramserver.py",
    ],
)
def test_final_runtime_migration_batch_uses_ci_aware_default_runtime_backend(
    test_path,
):
    text = Path(test_path).read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_identityserver_uses_ci_aware_default_runtime_backend():
    text = Path("tests/integration_tests/test_identityserver.py").read_text(
        encoding="utf-8"
    )

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_accserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_accserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_accserver.py",
            "label": "accserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_accserver.py",
            "label": "accserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_brickadiaserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_brickadiaserver.py" not in backlog


def test_brickadiaserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_brickadiaserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_brickadiaserver.py",
            "label": "brickadiaserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_brickadiaserver.py",
            "label": "brickadiaserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_btlserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_btlserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_btlserver.py",
            "label": "btlserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_btlserver.py",
            "label": "btlserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_bbserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_bbserver.py" not in backlog


def test_bbserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_bbserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_bbserver.py",
            "label": "bbserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_bbserver.py",
            "label": "bbserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_battlecryoffreedomserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_battlecryoffreedomserver.py" not in backlog


def test_battlecryoffreedomserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_battlecryoffreedomserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_battlecryoffreedomserver.py",
            "label": "battlecryoffreedomserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_battlecryoffreedomserver.py",
            "label": "battlecryoffreedomserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_blackops3server_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_blackops3server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_blackops3server.py",
            "label": "blackops3server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_blackops3server.py",
            "label": "blackops3server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_source_shared_batch_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        [
            "tests/integration_tests/test_cssserver.py",
            "tests/integration_tests/test_dodsserver.py",
            "tests/integration_tests/test_hl2dmserver.py",
            "tests/integration_tests/test_nmrihserver.py",
        ],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_cssserver.py",
            "label": "cssserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_cssserver.py",
            "label": "cssserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 3,
            "files": "tests/integration_tests/test_dodsserver.py",
            "label": "dodsserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 4,
            "files": "tests/integration_tests/test_dodsserver.py",
            "label": "dodsserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 5,
            "files": "tests/integration_tests/test_hl2dmserver.py",
            "label": "hl2dmserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 6,
            "files": "tests/integration_tests/test_hl2dmserver.py",
            "label": "hl2dmserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 7,
            "files": "tests/integration_tests/test_nmrihserver.py",
            "label": "nmrihserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 8,
            "files": "tests/integration_tests/test_nmrihserver.py",
            "label": "nmrihserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_fofserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_fofserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_fofserver.py",
            "label": "fofserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_fofserver.py",
            "label": "fofserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_aloftserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_aloftserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_aloftserver.py",
            "label": "aloftserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_aloftserver.py",
            "label": "aloftserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_svenserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_svenserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_svenserver.py",
            "label": "svenserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_svenserver.py",
            "label": "svenserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_insserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_insserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_insserver.py",
            "label": "insserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_insserver.py",
            "label": "insserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_inssserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_inssserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_inssserver.py",
            "label": "inssserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_inssserver.py",
            "label": "inssserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_goldsrc_batch_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        [
            "tests/integration_tests/test_ahlserver.py",
            "tests/integration_tests/test_bdserver.py",
            "tests/integration_tests/test_csserver.py",
            "tests/integration_tests/test_csczserver.py",
            "tests/integration_tests/test_dmcserver.py",
            "tests/integration_tests/test_dodserver.py",
            "tests/integration_tests/test_hldmserver.py",
        ],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_ahlserver.py",
            "label": "ahlserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_ahlserver.py",
            "label": "ahlserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 3,
            "files": "tests/integration_tests/test_bdserver.py",
            "label": "bdserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 4,
            "files": "tests/integration_tests/test_bdserver.py",
            "label": "bdserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 5,
            "files": "tests/integration_tests/test_csczserver.py",
            "label": "csczserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 6,
            "files": "tests/integration_tests/test_csczserver.py",
            "label": "csczserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 7,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 8,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 9,
            "files": "tests/integration_tests/test_dmcserver.py",
            "label": "dmcserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 10,
            "files": "tests/integration_tests/test_dmcserver.py",
            "label": "dmcserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 11,
            "files": "tests/integration_tests/test_dodserver.py",
            "label": "dodserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 12,
            "files": "tests/integration_tests/test_dodserver.py",
            "label": "dodserver-docker",
            "runtime_backend": "docker",
        },
        {
            "batch": 13,
            "files": "tests/integration_tests/test_hldmserver.py",
            "label": "hldmserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 14,
            "files": "tests/integration_tests/test_hldmserver.py",
            "label": "hldmserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_csserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_csserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_csserver.py",
            "label": "csserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_hldmsserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_hldmsserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_hldmsserver.py",
            "label": "hldmsserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_hldmsserver.py",
            "label": "hldmsserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_ahlserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_ahlserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_acserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_acserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_l4dserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_l4dserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_l4dserver.py",
            "label": "l4dserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_l4dserver.py",
            "label": "l4dserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_counterstrike2_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_counterstrike2.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_counterstrike2.py",
            "label": "counterstrike2-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_counterstrike2.py",
            "label": "counterstrike2-docker",
            "runtime_backend": "docker",
        },
    ]


def test_acserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_acserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_acserver.py",
            "label": "acserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_acserver.py",
            "label": "acserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_counterstrikeglobaloffensive_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_counterstrikeglobaloffensive.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_counterstrikeglobaloffensive.py",
            "label": "counterstrikeglobaloffensive-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_counterstrikeglobaloffensive.py",
            "label": "counterstrikeglobaloffensive-docker",
            "runtime_backend": "docker",
        },
    ]


def test_emserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_emserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_emserver.py",
            "label": "emserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_emserver.py",
            "label": "emserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_dayzserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_dayzserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_dayzserver.py",
            "label": "dayzserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_dayzserver.py",
            "label": "dayzserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_mumbleserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_mumbleserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_mumbleserver.py",
            "label": "mumbleserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_mumbleserver.py",
            "label": "mumbleserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_ts3server_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_ts3server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_ts3server.py",
            "label": "ts3server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_ts3server.py",
            "label": "ts3server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_q3server_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_q3server.py" not in backlog


def test_qlserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_qlserver.py" not in backlog


def test_ut2k4server_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_ut2k4server.py" not in backlog


def test_mordserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_mordserver.py" not in backlog


def test_atsserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_atsserver.py" not in backlog


def test_q2server_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_q2server.py" not in backlog


def test_jk2server_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_jk2server.py" not in backlog


def test_rtcwserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_rtcwserver.py" not in backlog


def test_q2server_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_q2server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_q2server.py",
            "label": "q2server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_q2server.py",
            "label": "q2server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_jk2server_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_jk2server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_jk2server.py",
            "label": "jk2server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_jk2server.py",
            "label": "jk2server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_rtcwserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_rtcwserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_rtcwserver.py",
            "label": "rtcwserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_rtcwserver.py",
            "label": "rtcwserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_q3server_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_q3server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_q3server.py",
            "label": "q3server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_q3server.py",
            "label": "q3server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_qlserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_qlserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_qlserver.py",
            "label": "qlserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_qlserver.py",
            "label": "qlserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_ut2k4server_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_ut2k4server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_ut2k4server.py",
            "label": "ut2k4server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_ut2k4server.py",
            "label": "ut2k4server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_mordserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_mordserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_mordserver.py",
            "label": "mordserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_mordserver.py",
            "label": "mordserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_atsserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_atsserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_atsserver.py",
            "label": "atsserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_atsserver.py",
            "label": "atsserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_necserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_necserver.py" not in backlog


def test_abfserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_abfserver.py" not in backlog


def test_avserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_avserver.py" not in backlog


def test_necserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_necserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_necserver.py",
            "label": "necserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_necserver.py",
            "label": "necserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_abfserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_abfserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_abfserver.py",
            "label": "abfserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_abfserver.py",
            "label": "abfserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_avserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_avserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_avserver.py",
            "label": "avserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_avserver.py",
            "label": "avserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_askaserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_askaserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_askaserver.py",
            "label": "askaserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_askaserver.py",
            "label": "askaserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_valheim_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_valheim.py"],
        repo_root=Path("."),
        heavy_only=True,
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_valheim.py",
            "label": "valheim-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_valheim.py",
            "label": "valheim-docker",
            "runtime_backend": "docker",
        },
    ]


def test_rust_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_rust.py"],
        repo_root=Path("."),
        heavy_only=True,
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_rust.py",
            "label": "rust-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_rust.py",
            "label": "rust-docker",
            "runtime_backend": "docker",
        },
    ]


def test_tf2_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_tf2.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_tf2.py",
            "label": "tf2-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_tf2.py",
            "label": "tf2-docker",
            "runtime_backend": "docker",
        },
    ]


def test_tf2cserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_tf2cserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_tf2cserver.py",
            "label": "tf2cserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_tf2cserver.py",
            "label": "tf2cserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_ahl2server_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_ahl2server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_ahl2server.py",
            "label": "ahl2server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_ahl2server.py",
            "label": "ahl2server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_l4d2server_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_l4d2server.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_l4d2server.py",
            "label": "l4d2server-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_l4d2server.py",
            "label": "l4d2server-docker",
            "runtime_backend": "docker",
        },
    ]


def test_opforserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_opforserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_opforserver.py",
            "label": "opforserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_opforserver.py",
            "label": "opforserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_tfcserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_tfcserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_tfcserver.py",
            "label": "tfcserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_tfcserver.py",
            "label": "tfcserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_battlebitserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_battlebitserver.py" not in backlog


def test_battlebitserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_battlebitserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_battlebitserver.py",
            "label": "battlebitserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_battlebitserver.py",
            "label": "battlebitserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_bfvserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_bfvserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_bfvserver.py",
            "label": "bfvserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_bfvserver.py",
            "label": "bfvserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_qwserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_qwserver.py" not in backlog


def test_qwserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_qwserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_qwserver.py",
            "label": "qwserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_qwserver.py",
            "label": "qwserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_ricochetserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_ricochetserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_ricochetserver.py",
            "label": "ricochetserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_ricochetserver.py",
            "label": "ricochetserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_doiserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_doiserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_doiserver.py",
            "label": "doiserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_doiserver.py",
            "label": "doiserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_pvkiiserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_pvkiiserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_pvkiiserver.py",
            "label": "pvkiiserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_pvkiiserver.py",
            "label": "pvkiiserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_gmodserver_builds_process_and_docker_dual_lanes_as_a_single_slice():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_gmodserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_gmodserver.py",
            "label": "gmodserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_gmodserver.py",
            "label": "gmodserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_goldeneyesourceserver_builds_process_and_docker_dual_lanes():
    routing = load_routing_module()

    matrix = routing.build_integration_matrix(
        ["tests/integration_tests/test_goldeneyesourceserver.py"],
        repo_root=Path("."),
    )

    assert matrix["include"] == [
        {
            "batch": 1,
            "files": "tests/integration_tests/test_goldeneyesourceserver.py",
            "label": "goldeneyesourceserver-process",
            "runtime_backend": "process",
        },
        {
            "batch": 2,
            "files": "tests/integration_tests/test_goldeneyesourceserver.py",
            "label": "goldeneyesourceserver-docker",
            "runtime_backend": "docker",
        },
    ]


def test_doiserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_doiserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_emserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_emserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_dayzserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_dayzserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_gmodserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_gmodserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_blackops3server_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_blackops3server.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_ts3server_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_ts3server.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_q2server_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_q2server.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_ut2k4server_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_ut2k4server.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_qlserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_qlserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_mordserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_mordserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_atsserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_atsserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_counterstrikeglobaloffensive_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_counterstrikeglobaloffensive.py").read_text(
        encoding="utf-8"
    )

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_inssserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_inssserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_jk2server_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_jk2server.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_avserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_avserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_bfvserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_bfvserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_bmdmserver_keeps_process_runtime_fallback():
    text = Path("tests/integration_tests/test_bmdmserver.py").read_text(encoding="utf-8")

    assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
    assert "default_runtime_backend()" in text
    assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_dual_lane_files_keep_process_runtime_fallback():
    assert True


def test_dual_lane_ci_default_runtime_backend_files_use_helper():
    for path in (
        Path("tests/integration_tests/test_alienarenaserver.py"),
        Path("tests/integration_tests/test_armarserver.py"),
        Path("tests/integration_tests/test_jk2server.py"),
        Path("tests/integration_tests/test_minecraft_bungeecord.py"),
        Path("tests/integration_tests/test_minecraft_custom.py"),
        Path("tests/integration_tests/test_minecraft_paper.py"),
        Path("tests/integration_tests/test_minecraft_tekkit.py"),
        Path("tests/integration_tests/test_minecraft_vanilla.py"),
        Path("tests/integration_tests/test_minecraft_velocity.py"),
        Path("tests/integration_tests/test_minecraft_waterfall.py"),
        Path("tests/integration_tests/test_necserver.py"),
        Path("tests/integration_tests/test_q2server.py"),
        Path("tests/integration_tests/test_q3server.py"),
        Path("tests/integration_tests/test_q4server.py"),
        Path("tests/integration_tests/test_qlserver.py"),
        Path("tests/integration_tests/test_qwserver.py"),
        Path("tests/integration_tests/test_rtcwserver.py"),
        Path("tests/integration_tests/test_ts3server.py"),
        Path("tests/integration_tests/test_ut99server.py"),
        Path("tests/integration_tests/test_wetserver.py"),
        Path("tests/integration_tests/test_wfserver.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
        assert "default_runtime_backend()" in text
        assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_dual_lane_ci_default_runtime_backend_additional_files_use_helper():
    for path in (
        Path("tests/integration_tests/test_argoserver.py"),
        Path("tests/integration_tests/test_blackwakeserver.py"),
        Path("tests/integration_tests/test_colserver.py"),
        Path("tests/integration_tests/test_conanexiles.py"),
        Path("tests/integration_tests/test_cryofallserver.py"),
        Path("tests/integration_tests/test_dabserver.py"),
        Path("tests/integration_tests/test_dysserver.py"),
        Path("tests/integration_tests/test_ecoserver.py"),
        Path("tests/integration_tests/test_enshrouded.py"),
        Path("tests/integration_tests/test_etlegacyserver.py"),
        Path("tests/integration_tests/test_groundbranchserver.py"),
        Path("tests/integration_tests/test_hurtworldserver.py"),
        Path("tests/integration_tests/test_hzserver.py"),
        Path("tests/integration_tests/test_icarusserver.py"),
        Path("tests/integration_tests/test_iosserver.py"),
        Path("tests/integration_tests/test_jc2server.py"),
        Path("tests/integration_tests/test_miscreatedserver.py"),
        Path("tests/integration_tests/test_mohaaserver.py"),
        Path("tests/integration_tests/test_mtaserver.py"),
        Path("tests/integration_tests/test_nightingale.py"),
        Path("tests/integration_tests/test_noonesurvivedserver.py"),
        Path("tests/integration_tests/test_notdserver.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
        assert "default_runtime_backend()" in text
        assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_dual_lane_ci_default_runtime_backend_more_files_use_helper():
    for path in (
        Path("tests/integration_tests/test_coduoserver.py"),
        Path("tests/integration_tests/test_codwawserver.py"),
        Path("tests/integration_tests/test_darkandlightserver.py"),
        Path("tests/integration_tests/test_deadpolyserver.py"),
        Path("tests/integration_tests/test_bsserver.py"),
        Path("tests/integration_tests/test_btserver.py"),
        Path("tests/integration_tests/test_saleblazersserver.py"),
        Path("tests/integration_tests/test_sampserver.py"),
        Path("tests/integration_tests/test_satisfactory.py"),
        Path("tests/integration_tests/test_sbotsserver.py"),
        Path("tests/integration_tests/test_scpslserver.py"),
        Path("tests/integration_tests/test_sevendaystodie.py"),
        Path("tests/integration_tests/test_silicaserver.py"),
        Path("tests/integration_tests/test_smallandserver.py"),
        Path("tests/integration_tests/test_sfcserver.py"),
        Path("tests/integration_tests/test_skyrimtogetherrebornserver.py"),
        Path("tests/integration_tests/test_solserver.py"),
        Path("tests/integration_tests/test_squad44server.py"),
        Path("tests/integration_tests/test_squadserver.py"),
        Path("tests/integration_tests/test_ss14server.py"),
        Path("tests/integration_tests/test_starbound.py"),
        Path("tests/integration_tests/test_stationeersserver.py"),
        Path("tests/integration_tests/test_staxelserver.py"),
        Path("tests/integration_tests/test_stnserver.py"),
        Path("tests/integration_tests/test_stormworksserver.py"),
        Path("tests/integration_tests/test_sunkenlandserver.py"),
        Path("tests/integration_tests/test_terraria_vanilla.py"),
        Path("tests/integration_tests/test_tf2_mods.py"),
        Path("tests/integration_tests/test_theforestserver.py"),
        Path("tests/integration_tests/test_thefrontserver.py"),
        Path("tests/integration_tests/test_trackmaniaserver.py"),
        Path("tests/integration_tests/test_terratechworldsserver.py"),
        Path("tests/integration_tests/test_tsserver.py"),
        Path("tests/integration_tests/test_tuserver.py"),
        Path("tests/integration_tests/test_twserver.py"),
        Path("tests/integration_tests/test_unturned.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
        assert "default_runtime_backend()" in text
        assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_selected_docker_sensitive_integration_tests_wait_on_declared_info_surface():
    expected_protocols = {
        Path("tests/integration_tests/test_medievalengineersserver.py"): "tcp",
        Path("tests/integration_tests/test_memoriesofmarsserver.py"): "a2s",
        Path("tests/integration_tests/test_silicaserver.py"): "a2s",
        Path("tests/integration_tests/test_solserver.py"): "a2s",
    }

    for path, protocol in expected_protocols.items():
        text = path.read_text(encoding="utf-8")
        assert "wait_for_info_protocol" in text
        assert f'wait_for_info_protocol(env, server_name, "{protocol}"' in text
        assert 'wait_for_a2s_ready("127.0.0.1"' not in text
        assert 'wait_for_tcp_open("127.0.0.1"' not in text


def test_dual_lane_ci_default_runtime_backend_even_more_files_use_helper():
    for path in (
        Path("tests/integration_tests/test_ahlserver.py"),
        Path("tests/integration_tests/test_acserver.py"),
        Path("tests/integration_tests/test_doiserver.py"),
        Path("tests/integration_tests/test_emserver.py"),
        Path("tests/integration_tests/test_dayzserver.py"),
        Path("tests/integration_tests/test_gmodserver.py"),
        Path("tests/integration_tests/test_blackops3server.py"),
        Path("tests/integration_tests/test_inssserver.py"),
        Path("tests/integration_tests/test_avserver.py"),
        Path("tests/integration_tests/test_bfvserver.py"),
        Path("tests/integration_tests/test_bmdmserver.py"),
        Path("tests/integration_tests/test_ahl2server.py"),
        Path("tests/integration_tests/test_askaserver.py"),
        Path("tests/integration_tests/test_valheim.py"),
        Path("tests/integration_tests/test_rust.py"),
        Path("tests/integration_tests/test_tf2.py"),
        Path("tests/integration_tests/test_tf2cserver.py"),
        Path("tests/integration_tests/test_l4d2server.py"),
        Path("tests/integration_tests/test_opforserver.py"),
        Path("tests/integration_tests/test_tfcserver.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "ALPHAGSM_TEST_RUNTIME_BACKEND" in text
        assert "default_runtime_backend()" in text
        assert 'os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")' not in text


def test_dual_lane_subset_stays_separate_from_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))
    dual_lane = set(routing.PROCESS_PASSED_DOCKER_PENDING_DUAL_LANE_TESTS)

    assert backlog.isdisjoint(dual_lane)


def test_port_manager_source_collision_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_port_manager_source_collision.py" not in backlog


def test_argoserver_and_blackwakeserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_argoserver.py",
        "tests/integration_tests/test_blackwakeserver.py",
    ):
        assert test_path not in backlog


def test_cod2server_and_cod4server_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_cod2server.py",
        "tests/integration_tests/test_cod4server.py",
    ):
        assert test_path not in backlog


def test_citadelserver_and_codserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_citadelserver.py",
        "tests/integration_tests/test_codserver.py",
    ):
        assert test_path not in backlog


def test_colserver_and_conanexiles_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_cryofallserver.py",
        "tests/integration_tests/test_dabserver.py",
        "tests/integration_tests/test_dysserver.py",
        "tests/integration_tests/test_colserver.py",
        "tests/integration_tests/test_conanexiles.py",
    ):
        assert test_path not in backlog


def test_enshrouded_and_etlegacyserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_ecoserver.py",
        "tests/integration_tests/test_enshrouded.py",
        "tests/integration_tests/test_etlegacyserver.py",
    ):
        assert test_path not in backlog


def test_coduoserver_and_codwawserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_coduoserver.py",
        "tests/integration_tests/test_codwawserver.py",
    ):
        assert test_path not in backlog


def test_darkandlightserver_and_deadpolyserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_darkandlightserver.py",
        "tests/integration_tests/test_deadpolyserver.py",
    ):
        assert test_path not in backlog


def test_bsserver_and_btserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_bsserver.py",
        "tests/integration_tests/test_btserver.py",
    ):
        assert test_path not in backlog


def test_saleblazers_samp_satisfactory_sbots_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_saleblazersserver.py",
        "tests/integration_tests/test_sampserver.py",
        "tests/integration_tests/test_satisfactory.py",
        "tests/integration_tests/test_sbotsserver.py",
    ):
        assert test_path not in backlog


def test_scpsl_sevendaystodie_silicaserver_smallandserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_scpslserver.py",
        "tests/integration_tests/test_sevendaystodie.py",
        "tests/integration_tests/test_silicaserver.py",
        "tests/integration_tests/test_smallandserver.py",
    ):
        assert test_path not in backlog


def test_sfcserver_and_skyrimtogetherrebornserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_sfcserver.py",
        "tests/integration_tests/test_skyrimtogetherrebornserver.py",
    ):
        assert test_path not in backlog


def test_solserver_and_squad44server_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_solserver.py",
        "tests/integration_tests/test_squad44server.py",
    ):
        assert test_path not in backlog


def test_squadserver_moves_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    assert "tests/integration_tests/test_squadserver.py" not in backlog


def test_ss14server_and_starbound_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_ss14server.py",
        "tests/integration_tests/test_starbound.py",
    ):
        assert test_path not in backlog


def test_stationeersserver_and_staxelserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_stationeersserver.py",
        "tests/integration_tests/test_staxelserver.py",
    ):
        assert test_path not in backlog


def test_stnserver_and_stormworksserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_stnserver.py",
        "tests/integration_tests/test_stormworksserver.py",
    ):
        assert test_path not in backlog


def test_sunkenlandserver_and_terraria_vanilla_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_sunkenlandserver.py",
        "tests/integration_tests/test_terraria_vanilla.py",
    ):
        assert test_path not in backlog


def test_tf2_mods_and_theforestserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_tf2_mods.py",
        "tests/integration_tests/test_theforestserver.py",
    ):
        assert test_path not in backlog


def test_thefrontserver_and_trackmaniaserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_thefrontserver.py",
        "tests/integration_tests/test_trackmaniaserver.py",
    ):
        assert test_path not in backlog


def test_terratechworldsserver_and_tsserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_terratechworldsserver.py",
        "tests/integration_tests/test_tsserver.py",
    ):
        assert test_path not in backlog


def test_tuserver_and_twserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_tuserver.py",
        "tests/integration_tests/test_twserver.py",
    ):
        assert test_path not in backlog


def test_unturned_and_ut99server_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_unturned.py",
        "tests/integration_tests/test_ut99server.py",
    ):
        assert test_path not in backlog


def test_vsserver_and_warbandserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_vsserver.py",
        "tests/integration_tests/test_warbandserver.py",
    ):
        assert test_path not in backlog


def test_wetserver_and_wfserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_wetserver.py",
        "tests/integration_tests/test_wfserver.py",
    ):
        assert test_path not in backlog


def test_wurmserver_and_zmrserver_move_out_of_docker_enablement_backlog():
    routing = load_routing_module()

    backlog = set(routing.docker_enablement_backlog_tests(repo_root=Path(".")))

    for test_path in (
        "tests/integration_tests/test_wurmserver.py",
        "tests/integration_tests/test_zmrserver.py",
    ):
        assert test_path not in backlog


def test_workflow_changes_force_full_linux_game_test_run():
    routing = load_routing_module()

    result = routing.classify_changed_files(
        [".github/workflows/unittest.yaml"],
        repo_root=Path("."),
    )

    assert result["mode"] == "all"


def test_unittest_workflow_declares_classify_changes_job():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "classify-changes:" in text


def test_unittest_workflow_cancels_superseded_pr_runs():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "concurrency:" in text
    assert "group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}" in text
    assert "cancel-in-progress: true" in text


def test_unittest_workflow_routes_linux_game_matrices_from_classifier_outputs():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "scripts/ci_game_test_routing.py" in text
    assert "needs: [unit-test, lint, coverage, classify-changes]" in text
    assert "needs.classify-changes.outputs.smoke_standard_matrix" in text
    assert "needs.classify-changes.outputs.smoke_heavy_matrix" in text
    assert "needs.classify-changes.outputs.integration_standard_matrix" in text
    assert "needs.classify-changes.outputs.integration_heavy_matrix" in text
    assert "if: needs.discover-smoke-tests.outputs.has_standard_tests == 'true'" in text
    assert "if: needs.discover-smoke-tests.outputs.has_heavy_tests == 'true'" in text
    assert "if: needs.discover-integration-tests.outputs.has_standard_tests == 'true'" in text
    assert "if: needs.discover-integration-tests.outputs.has_heavy_tests == 'true'" in text


def test_unittest_workflow_routes_heavy_game_jobs_to_configurable_runner_labels():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "vars.ALPHAGSM_HEAVY_RUNNER_LABELS_JSON" in text
    assert "runs-on: ${{ fromJson(vars.ALPHAGSM_HEAVY_RUNNER_LABELS_JSON || '[\"ubuntu-latest\"]') }}" in text
    assert "smoke-test-heavy:" in text
    assert "integration-test-heavy:" in text


def test_unittest_workflow_keeps_backend_and_cross_platform_jobs_unconditional():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "backend-smoke-test:" in text
    assert "backend-integration-test:" in text
    assert "windows-minecraft-integration:" in text
    assert "macos-minecraft-integration:" in text
    assert "needs: [unit-test, lint, coverage, build-java-runtime]" in text
    assert (
        "needs: [unit-test, lint, coverage, build-integration-image, "
        "build-java-runtime, build-steamcmd-linux-runtime, build-wine-proton-runtime]"
    ) in text
    assert "needs: [unit-test, lint, coverage]" in text


def test_unittest_workflow_frees_runner_disk_before_linux_smoke_batches():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Free runner disk space for large Docker smoke coverage" in text
    assert "sudo rm -rf /usr/share/dotnet /opt/ghc /usr/local/lib/android /usr/share/swift" in text
    assert "df -h /" in text
