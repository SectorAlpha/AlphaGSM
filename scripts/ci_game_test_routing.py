#!/usr/bin/env python3
"""Route Linux game smoke and integration coverage based on changed files."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_TEST_DIR = REPO_ROOT / "tests" / "smoke_tests"
INTEGRATION_TEST_DIR = REPO_ROOT / "tests" / "integration_tests"
GAME_MODULE_DIR = REPO_ROOT / "src" / "gamemodules"
FULL_RUN_MODE = "all"
SKIP_MODE = "skip"
TARGETED_MODE = "targeted"
DOC_BASENAMES = {"README.md", "DEVELOPERS.md", "SKILLS.md"}
SLOW_TESTS = [
    "test_rs2server.py",
    "test_scumserver.py",
    "test_sevendaystodie.py",
    "test_palworld.py",
    "test_rust.py",
    "test_arksurvivalascended.py",
    "test_btserver.py",
    "test_empyrionserver.py",
    "test_enshrouded.py",
    "test_readyornotserver.py",
    "test_sniperelite4server.py",
    "test_sonsoftheforestserver.py",
    "test_valheim.py",
    "test_blackops3server.py",
    "test_mythofempiresserver.py",
]
HEAVY_SMOKE_TESTS = {
    "run_arksurvivalascended.sh",
    "run_btserver.sh",
    "run_empyrionserver.sh",
    "run_enshrouded.sh",
    "run_palworld.sh",
    "run_readyornotserver.sh",
    "run_rs2server.sh",
    "run_rust.sh",
    "run_scumserver.sh",
    "run_sevendaystodie.sh",
    "run_sniperelite4server.sh",
    "run_sonsoftheforestserver.sh",
    "run_valheim.sh",
    "run_blackops3server.sh",
    "run_mythofempiresserver.sh",
}
MODULE_ALIASES = {
    "cs2server": ["counterstrike2"],
    "csgoserver": ["counterstrikeglobaloffensive"],
    "csgo": ["counterstrikeglobaloffensive"],
    "risingstorm2vietnam": ["rs2server"],
    "tf2server": ["teamfortress2"],
}
PROCESS_PASSED_DOCKER_PENDING_DUAL_LANE_TESTS: tuple[str, ...] = (
    "tests/integration_tests/test_aloftserver.py",
    "tests/integration_tests/test_ahlserver.py",
    "tests/integration_tests/test_ahl2server.py",
    "tests/integration_tests/test_acserver.py",
    "tests/integration_tests/test_accserver.py",
    "tests/integration_tests/test_abfserver.py",
    "tests/integration_tests/test_avserver.py",
    "tests/integration_tests/test_alienarenaserver.py",
    "tests/integration_tests/test_askaserver.py",
    "tests/integration_tests/test_atsserver.py",
    "tests/integration_tests/test_argoserver.py",
    "tests/integration_tests/test_arma2coserver.py",
    "tests/integration_tests/test_arma3_altislife.py",
    "tests/integration_tests/test_arma3_desolationredux.py",
    "tests/integration_tests/test_arma3_epoch.py",
    "tests/integration_tests/test_arma3_exile.py",
    "tests/integration_tests/test_arma3_headless.py",
    "tests/integration_tests/test_arma3_vanilla.py",
    "tests/integration_tests/test_arma3_wasteland.py",
    "tests/integration_tests/test_arma3altislifeserver.py",
    "tests/integration_tests/test_arma3desolationreduxserver.py",
    "tests/integration_tests/test_arma3epochserver.py",
    "tests/integration_tests/test_arma3exileserver.py",
    "tests/integration_tests/test_arma3headlessserver.py",
    "tests/integration_tests/test_arma3server.py",
    "tests/integration_tests/test_arma3wastelandserver.py",
    "tests/integration_tests/test_armarserver.py",
    "tests/integration_tests/test_bdserver.py",
    "tests/integration_tests/test_bmdmserver.py",
    "tests/integration_tests/test_bf1942server.py",
    "tests/integration_tests/test_bfvserver.py",
    "tests/integration_tests/test_bbserver.py",
    "tests/integration_tests/test_bsserver.py",
    "tests/integration_tests/test_bobserver.py",
    "tests/integration_tests/test_boserver.py",
    "tests/integration_tests/test_cod2server.py",
    "tests/integration_tests/test_cod4server.py",
    "tests/integration_tests/test_codserver.py",
    "tests/integration_tests/test_coduoserver.py",
    "tests/integration_tests/test_codwawserver.py",
    "tests/integration_tests/test_brokeprotocolserver.py",
    "tests/integration_tests/test_battlecryoffreedomserver.py",
    "tests/integration_tests/test_battlebitserver.py",
    "tests/integration_tests/test_bb2server.py",
    "tests/integration_tests/test_brickadiaserver.py",
    "tests/integration_tests/test_btlserver.py",
    "tests/integration_tests/test_btserver.py",
    "tests/integration_tests/test_ccserver.py",
    "tests/integration_tests/test_ckserver.py",
    "tests/integration_tests/test_csserver.py",
    "tests/integration_tests/test_counterstrike2.py",
    "tests/integration_tests/test_counterstrikeglobaloffensive.py",
    "tests/integration_tests/test_csczserver.py",
    "tests/integration_tests/test_chivalryserver.py",
    "tests/integration_tests/test_craftopiaserver.py",
    "tests/integration_tests/test_dayzserver.py",
    "tests/integration_tests/test_dayzarma2epochserver.py",
    "tests/integration_tests/test_dayofdragonsserver.py",
    "tests/integration_tests/test_deadmatterserver.py",
    "tests/integration_tests/test_cryofallserver.py",
    "tests/integration_tests/test_dabserver.py",
    "tests/integration_tests/test_dysserver.py",
    "tests/integration_tests/test_colserver.py",
    "tests/integration_tests/test_conanexiles.py",
    "tests/integration_tests/test_deadpolyserver.py",
    "tests/integration_tests/test_doiserver.py",
    "tests/integration_tests/test_dmcserver.py",
    "tests/integration_tests/test_dodserver.py",
    "tests/integration_tests/test_ducksideserver.py",
    "tests/integration_tests/test_dstserver.py",
    "tests/integration_tests/test_emserver.py",
    "tests/integration_tests/test_groundbranchserver.py",
    "tests/integration_tests/test_hurtworldserver.py",
    "tests/integration_tests/test_hzserver.py",
    "tests/integration_tests/test_icarusserver.py",
    "tests/integration_tests/test_etlegacyserver.py",
    "tests/integration_tests/test_ets2server.py",
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
    "tests/integration_tests/test_hellletlooseserver.py",
    "tests/integration_tests/test_hldmserver.py",
    "tests/integration_tests/test_hldmsserver.py",
    "tests/integration_tests/test_hogwarpserver.py",
    "tests/integration_tests/test_identityserver.py",
    "tests/integration_tests/test_insserver.py",
    "tests/integration_tests/test_inssserver.py",
    "tests/integration_tests/test_interstellarriftserver.py",
    "tests/integration_tests/test_jc3server.py",
    "tests/integration_tests/test_jk2server.py",
    "tests/integration_tests/test_kf2server.py",
    "tests/integration_tests/test_kerbalspaceprogramserver.py",
    "tests/integration_tests/test_kfserver.py",
    "tests/integration_tests/test_l4dserver.py",
    "tests/integration_tests/test_l4d2server.py",
    "tests/integration_tests/test_lifeisfeudalserver.py",
    "tests/integration_tests/test_longvinterserver.py",
    "tests/integration_tests/test_medievalengineersserver.py",
    "tests/integration_tests/test_minecraft_bedrock.py",
    "tests/integration_tests/test_minecraft_bungeecord.py",
    "tests/integration_tests/test_minecraft_custom.py",
    "tests/integration_tests/test_minecraft_paper.py",
    "tests/integration_tests/test_minecraft_tekkit.py",
    "tests/integration_tests/test_minecraft_vanilla.py",
    "tests/integration_tests/test_minecraft_velocity.py",
    "tests/integration_tests/test_minecraft_waterfall.py",
    "tests/integration_tests/test_memoriesofmarsserver.py",
    "tests/integration_tests/test_motortownserver.py",
    "tests/integration_tests/test_mordserver.py",
    "tests/integration_tests/test_mohaaserver.py",
    "tests/integration_tests/test_mtaserver.py",
    "tests/integration_tests/test_nightingale.py",
    "tests/integration_tests/test_noonesurvivedserver.py",
    "tests/integration_tests/test_notdserver.py",
    "tests/integration_tests/test_mw3server.py",
    "tests/integration_tests/test_mxbikesserver.py",
    "tests/integration_tests/test_necserver.py",
    "tests/integration_tests/test_ndserver.py",
    "tests/integration_tests/test_ns2cserver.py",
    "tests/integration_tests/test_nsserver.py",
    "tests/integration_tests/test_ns2server.py",
    "tests/integration_tests/test_onsetserver.py",
    "tests/integration_tests/test_pathoftitansserver.py",
    "tests/integration_tests/test_gmodserver.py",
    "tests/integration_tests/test_opforserver.py",
    "tests/integration_tests/test_outpostzeroserver.py",
    "tests/integration_tests/test_pcarserver.py",
    "tests/integration_tests/test_pcars2server.py",
    "tests/integration_tests/test_pixarkserver.py",
    "tests/integration_tests/test_police1013server.py",
    "tests/integration_tests/test_primalcarnageextinctionserver.py",
    "tests/integration_tests/test_projectzomboid.py",
    "tests/integration_tests/test_ohdserver.py",
    "tests/integration_tests/test_palworld.py",
    "tests/integration_tests/test_pvrserver.py",
    "tests/integration_tests/test_q2server.py",
    "tests/integration_tests/test_pvkiiserver.py",
    "tests/integration_tests/test_rwserver.py",
    "tests/integration_tests/test_q3server.py",
    "tests/integration_tests/test_qlserver.py",
    "tests/integration_tests/test_q4server.py",
    "tests/integration_tests/test_rtcwserver.py",
    "tests/integration_tests/test_qwserver.py",
    "tests/integration_tests/test_redmserver.py",
    "tests/integration_tests/test_reignofkingsserver.py",
    "tests/integration_tests/test_ricochetserver.py",
    "tests/integration_tests/test_ror2server.py",
    "tests/integration_tests/test_roserver.py",
    "tests/integration_tests/test_rimworldtogetherserver.py",
    "tests/integration_tests/test_port_manager_source_collision.py",
    "tests/integration_tests/test_scpslserver.py",
    "tests/integration_tests/test_sevendaystodie.py",
    "tests/integration_tests/test_seserver.py",
    "tests/integration_tests/test_saleblazersserver.py",
    "tests/integration_tests/test_sampserver.py",
    "tests/integration_tests/test_satisfactory.py",
    "tests/integration_tests/test_sbotsserver.py",
    "tests/integration_tests/test_sniperelite4server.py",
    "tests/integration_tests/test_sof2server.py",
    "tests/integration_tests/test_soulmask.py",
    "tests/integration_tests/test_sfcserver.py",
    "tests/integration_tests/test_skyrimtogetherrebornserver.py",
    "tests/integration_tests/test_silicaserver.py",
    "tests/integration_tests/test_smallandserver.py",
    "tests/integration_tests/test_solserver.py",
    "tests/integration_tests/test_squad44server.py",
    "tests/integration_tests/test_squadserver.py",
    "tests/integration_tests/test_ss14server.py",
    "tests/integration_tests/test_starbound.py",
    "tests/integration_tests/test_starruptureserver.py",
    "tests/integration_tests/test_stationeersserver.py",
    "tests/integration_tests/test_staxelserver.py",
    "tests/integration_tests/test_stnserver.py",
    "tests/integration_tests/test_stormworksserver.py",
    "tests/integration_tests/test_sunkenlandserver.py",
    "tests/integration_tests/test_subnauticaserver.py",
    "tests/integration_tests/test_subsistenceserver.py",
    "tests/integration_tests/test_terraria_vanilla.py",
    "tests/integration_tests/test_terraria_tshock.py",
    "tests/integration_tests/test_tf2_mods.py",
    "tests/integration_tests/test_theforestserver.py",
    "tests/integration_tests/test_thefrontserver.py",
    "tests/integration_tests/test_trackmaniaserver.py",
    "tests/integration_tests/test_terratechworldsserver.py",
    "tests/integration_tests/test_tsserver.py",
    "tests/integration_tests/test_tiserver.py",
    "tests/integration_tests/test_tuserver.py",
    "tests/integration_tests/test_twserver.py",
    "tests/integration_tests/test_unturned.py",
    "tests/integration_tests/test_ut99server.py",
    "tests/integration_tests/test_ut3server.py",
    "tests/integration_tests/test_vsserver.py",
    "tests/integration_tests/test_warbandserver.py",
    "tests/integration_tests/test_wetserver.py",
    "tests/integration_tests/test_wfserver.py",
    "tests/integration_tests/test_wreckfestserver.py",
    "tests/integration_tests/test_wurmserver.py",
    "tests/integration_tests/test_zmrserver.py",
    "tests/integration_tests/test_vintagestoryserver.py",
    "tests/integration_tests/test_veinserver.py",
    "tests/integration_tests/test_vrserver.py",
    "tests/integration_tests/test_zpsserver.py",
    "tests/integration_tests/test_svenserver.py",
    "tests/integration_tests/test_ts3server.py",
    "tests/integration_tests/test_rust.py",
    "tests/integration_tests/test_tf2.py",
    "tests/integration_tests/test_tf2cserver.py",
    "tests/integration_tests/test_tfcserver.py",
    "tests/integration_tests/test_ut2k4server.py",
    "tests/integration_tests/test_valheim.py",
    "tests/integration_tests/test_cssserver.py",
    "tests/integration_tests/test_dodsserver.py",
    "tests/integration_tests/test_hl2dmserver.py",
    "tests/integration_tests/test_nmrihserver.py",
)
SOURCE_FAMILY_BACKLOG = set()
DOCKER_DEFAULT_RUNTIME_TESTS = {
    "tests/integration_tests/test_archive_backed_installs.py",
    "tests/integration_tests/test_ark.py",
    "tests/integration_tests/test_arksurvivalascended.py",
    "tests/integration_tests/test_astroneerserver.py",
    "tests/integration_tests/test_atlasserver.py",
    "tests/integration_tests/test_bannerlordserver.py",
    "tests/integration_tests/test_citadelserver.py",
    "tests/integration_tests/test_darkandlightserver.py",
    "tests/integration_tests/test_ecoserver.py",
    "tests/integration_tests/test_empyrionserver.py",
    "tests/integration_tests/test_enshrouded.py",
    "tests/integration_tests/test_iosserver.py",
    "tests/integration_tests/test_jc2server.py",
    "tests/integration_tests/test_lastoasisserver.py",
    "tests/integration_tests/test_miscreatedserver.py",
    "tests/integration_tests/test_mumbleserver.py",
    "tests/integration_tests/test_readyornotserver.py",
    "tests/integration_tests/test_reignofdwarfserver.py",
    "tests/integration_tests/test_remnantsserver.py",
    "tests/integration_tests/test_returntomoriaserver.py",
    "tests/integration_tests/test_rs2server.py",
    "tests/integration_tests/test_scumserver.py",
    "tests/integration_tests/test_sonsoftheforestserver.py",
    "tests/integration_tests/test_blackops3server.py",
    "tests/integration_tests/test_blackwakeserver.py",
    "tests/integration_tests/test_mythofempiresserver.py",
    "tests/integration_tests/test_xntserver.py",
}


def normalize_repo_path(path: str) -> str:
    return PurePosixPath(path.strip()).as_posix()


def is_docs_only_path(path: str) -> bool:
    posix_path = PurePosixPath(normalize_repo_path(path))

    if not posix_path.parts:
        return False
    if posix_path.parts[0] in {"docs", "skills"}:
        return True
    if posix_path.name in DOC_BASENAMES:
        return True
    if posix_path.parts[0] == "docker" and posix_path.suffix == ".md":
        return True
    return False


def is_module_candidate(path: str) -> bool:
    posix_path = PurePosixPath(normalize_repo_path(path))
    return (
        len(posix_path.parts) >= 3
        and posix_path.parts[0] == "src"
        and posix_path.parts[1] == "gamemodules"
        and posix_path.suffix == ".py"
    )


def module_key_from_path(path: str) -> str:
    posix_path = PurePosixPath(normalize_repo_path(path))
    rel_parts = posix_path.parts[2:]
    if rel_parts and rel_parts[-1] == "main.py":
        rel_parts = rel_parts[:-1]
    return "_".join(PurePosixPath(*rel_parts).with_suffix("").parts)


def file_is_ambiguous_module_support(path: str) -> bool:
    posix_path = PurePosixPath(normalize_repo_path(path))
    return posix_path.name in {"__init__.py", "DEFAULT.py", "common.py"}


def candidate_names_for_module(path: str) -> list[str]:
    key = module_key_from_path(path)
    names = [key]
    names.extend(MODULE_ALIASES.get(key, []))
    seen: set[str] = set()
    ordered = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def resolve_module_targets(path: str, repo_root: Path | None = None) -> dict[str, list[str]] | None:
    root = repo_root or REPO_ROOT
    smoke_matches: list[str] = []
    integration_matches: list[str] = []

    if file_is_ambiguous_module_support(path):
        return None

    for candidate in candidate_names_for_module(path):
        smoke_path = root / "tests" / "smoke_tests" / f"run_{candidate}.sh"
        integration_path = root / "tests" / "integration_tests" / f"test_{candidate}.py"
        if smoke_path.exists():
            smoke_matches.append(smoke_path.relative_to(root).as_posix())
        if integration_path.exists():
            integration_matches.append(integration_path.relative_to(root).as_posix())

    if not smoke_matches and not integration_matches:
        return None

    return {
        "smoke_scripts": dedupe(smoke_matches),
        "integration_tests": dedupe(integration_matches),
    }


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def docker_enablement_backlog_tests(repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    dual_lane = set(PROCESS_PASSED_DOCKER_PENDING_DUAL_LANE_TESTS)
    return sorted(
        path.relative_to(root).as_posix()
        for path in (root / "tests" / "integration_tests").glob("test_*.py")
        if path.relative_to(root).as_posix() not in dual_lane
        and path.relative_to(root).as_posix() not in DOCKER_DEFAULT_RUNTIME_TESTS
    )


def docker_backlog_for_family(family_name: str, repo_root: Path | None = None) -> list[str]:
    backlog = set(docker_enablement_backlog_tests(repo_root=repo_root))
    if family_name == "source-family":
        return sorted(path for path in backlog if path in SOURCE_FAMILY_BACKLOG or "source" in path)
    return sorted(backlog)


def is_heavy_smoke_script(path: str) -> bool:
    return PurePosixPath(path).name in HEAVY_SMOKE_TESTS


def is_heavy_integration_test(path: str) -> bool:
    return PurePosixPath(path).name in set(SLOW_TESTS)


def partition_by_predicate(items: list[str], predicate) -> tuple[list[str], list[str]]:
    standard: list[str] = []
    heavy: list[str] = []
    for item in items:
        if predicate(item):
            heavy.append(item)
        else:
            standard.append(item)
    return standard, heavy


def _build_batched_matrix(paths: list[str], prefix: str, root: Path) -> dict[str, list[dict[str, str]]]:
    if not paths:
        return {"include": []}

    max_jobs = 40
    batch_size = max(1, math.ceil(len(paths) / max_jobs))
    include = []
    total = math.ceil(len(paths) / batch_size)
    for index in range(0, len(paths), batch_size):
        chunk = paths[index : index + batch_size]
        batch_number = index // batch_size + 1
        include.append(
            {
                "batch": batch_number,
                "label": f"batch-{batch_number}-of-{total}",
                prefix: " ".join(chunk),
            }
        )
    return {"include": include}


def _build_full_integration_matrix(paths: list[str], root: Path) -> dict[str, list[dict[str, str]]]:
    """Build the full matrix with explicit process and Docker dual lanes."""

    dual_lane = set(PROCESS_PASSED_DOCKER_PENDING_DUAL_LANE_TESTS)
    default_paths = [path for path in paths if path not in dual_lane]
    dual_paths = [path for path in paths if path in dual_lane]
    include: list[dict[str, str]] = []

    for runtime_backend, lane_paths in (
        (None, default_paths),
        ("process", dual_paths),
        ("docker", dual_paths),
    ):
        lane = _build_batched_matrix(lane_paths, "files", root)
        for entry in lane["include"]:
            entry = dict(entry)
            entry["batch"] = len(include) + 1
            if runtime_backend is not None:
                entry["runtime_backend"] = runtime_backend
                entry["label"] = f"{entry['label']}-{runtime_backend}"
            include.append(entry)

    return {"include": include}


def _build_targeted_matrix(paths: list[str], prefix: str, stem_prefix: str) -> dict[str, list[dict[str, str]]]:
    include = []
    for index, path in enumerate(sorted(paths), start=1):
        include.append(
            {
                "batch": index,
                prefix: path,
                "label": PurePosixPath(path).stem.replace(stem_prefix, ""),
            }
        )
    return {"include": include}


def _build_targeted_integration_matrix(paths: list[str]) -> dict[str, list[dict[str, str]]]:
    include = []
    dual_lane = set(PROCESS_PASSED_DOCKER_PENDING_DUAL_LANE_TESTS)

    for path in sorted(paths):
        base_label = PurePosixPath(path).stem.replace("test_", "")
        if path in dual_lane:
            for runtime_backend in ("process", "docker"):
                include.append(
                    {
                        "batch": len(include) + 1,
                        "files": path,
                        "label": f"{base_label}-{runtime_backend}",
                        "runtime_backend": runtime_backend,
                    }
                )
            continue

        include.append(
            {
                "batch": len(include) + 1,
                "files": path,
                "label": base_label,
            }
        )

    return {"include": include}


def classify_changed_files(changed_files: list[str], repo_root: Path | None = None) -> dict[str, object]:
    root = repo_root or REPO_ROOT
    normalized = dedupe([normalize_repo_path(path) for path in changed_files if path.strip()])
    non_docs = [path for path in normalized if not is_docs_only_path(path)]

    if not non_docs:
        return {
            "mode": SKIP_MODE,
            "smoke_scripts": [],
            "integration_tests": [],
            "changed_files": normalized,
        }

    if any(not is_module_candidate(path) for path in non_docs):
        return {
            "mode": FULL_RUN_MODE,
            "smoke_scripts": [],
            "integration_tests": [],
            "changed_files": normalized,
        }

    selected_smoke: list[str] = []
    selected_integration: list[str] = []
    for path in non_docs:
        targets = resolve_module_targets(path, repo_root=root)
        if targets is None:
            return {
                "mode": FULL_RUN_MODE,
                "smoke_scripts": [],
                "integration_tests": [],
                "changed_files": normalized,
            }
        selected_smoke.extend(targets["smoke_scripts"])
        selected_integration.extend(targets["integration_tests"])

    return {
        "mode": TARGETED_MODE,
        "smoke_scripts": dedupe(selected_smoke),
        "integration_tests": dedupe(selected_integration),
        "changed_files": normalized,
    }


def build_smoke_matrix(
    selected_scripts: list[str] | None = None,
    repo_root: Path | None = None,
    *,
    heavy_only: bool = False,
) -> dict[str, list[dict[str, str]]]:
    root = repo_root or REPO_ROOT
    scripts = selected_scripts
    if scripts is None:
        scripts = sorted(
            path.relative_to(root).as_posix()
            for path in (root / "tests" / "smoke_tests").glob("run_*.sh")
            if not path.name.startswith("run_backend_")
        )
        standard_scripts, heavy_scripts = partition_by_predicate(scripts, is_heavy_smoke_script)
        selected = heavy_scripts if heavy_only else standard_scripts
        return _build_batched_matrix(selected, "scripts", root)

    standard_scripts, heavy_scripts = partition_by_predicate(sorted(selected_scripts), is_heavy_smoke_script)
    selected = heavy_scripts if heavy_only else standard_scripts
    return _build_targeted_matrix(selected, "scripts", "run_")


def build_integration_matrix(
    selected_tests: list[str] | None = None,
    repo_root: Path | None = None,
    *,
    heavy_only: bool = False,
) -> dict[str, list[dict[str, str]]]:
    root = repo_root or REPO_ROOT
    if selected_tests is not None:
        standard_tests, heavy_tests = partition_by_predicate(sorted(selected_tests), is_heavy_integration_test)
        selected = heavy_tests if heavy_only else standard_tests
        return _build_targeted_integration_matrix(selected)

    all_tests = sorted(
        path.name for path in (root / "tests" / "integration_tests").glob("test_*.py")
    )
    slow_set = set(SLOW_TESTS)
    regular_tests = [test_name for test_name in all_tests if test_name not in slow_set]

    if heavy_only:
        slow_paths = []
        for test_name in SLOW_TESTS:
            if test_name in all_tests:
                slow_paths.append(f"tests/integration_tests/{test_name}")
        return _build_full_integration_matrix(slow_paths, root)

    regular_paths = [f"tests/integration_tests/{name}" for name in regular_tests]
    return _build_full_integration_matrix(regular_paths, root)


def git_changed_files(base_sha: str, head_sha: str, repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    try:
        merge_base_result = subprocess.run(
            ["git", "merge-base", base_sha, head_sha],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git merge-base failed for base={base_sha!r} head={head_sha!r}; "
            "ensure both commits are present (fetch-depth: 0 in checkout). "
            f"stderr: {exc.stderr.strip()}"
        ) from exc
    merge_base = merge_base_result.stdout.strip()
    result = subprocess.run(
        ["git", "diff", "--name-only", merge_base, head_sha],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def write_github_outputs(outputs: dict[str, str], github_output: str) -> None:
    with open(github_output, "a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={value}\n")


def build_outputs_for_changed_files(changed_files: list[str], repo_root: Path | None = None) -> dict[str, str]:
    classification = classify_changed_files(changed_files, repo_root=repo_root)
    mode = classification["mode"]
    if mode == SKIP_MODE:
        smoke_standard_matrix = {"include": []}
        smoke_heavy_matrix = {"include": []}
        integration_standard_matrix = {"include": []}
        integration_heavy_matrix = {"include": []}
    elif mode == TARGETED_MODE:
        smoke_standard_matrix = build_smoke_matrix(
            classification["smoke_scripts"], repo_root=repo_root, heavy_only=False
        )
        smoke_heavy_matrix = build_smoke_matrix(
            classification["smoke_scripts"], repo_root=repo_root, heavy_only=True
        )
        integration_standard_matrix = build_integration_matrix(
            classification["integration_tests"], repo_root=repo_root, heavy_only=False
        )
        integration_heavy_matrix = build_integration_matrix(
            classification["integration_tests"], repo_root=repo_root, heavy_only=True
        )
    else:
        smoke_standard_matrix = build_smoke_matrix(repo_root=repo_root, heavy_only=False)
        smoke_heavy_matrix = build_smoke_matrix(repo_root=repo_root, heavy_only=True)
        integration_standard_matrix = build_integration_matrix(repo_root=repo_root, heavy_only=False)
        integration_heavy_matrix = build_integration_matrix(repo_root=repo_root, heavy_only=True)

    return {
        "game_test_mode": mode,
        "has_smoke_standard_tests": str(bool(smoke_standard_matrix["include"])).lower(),
        "has_smoke_heavy_tests": str(bool(smoke_heavy_matrix["include"])).lower(),
        "has_integration_standard_tests": str(bool(integration_standard_matrix["include"])).lower(),
        "has_integration_heavy_tests": str(bool(integration_heavy_matrix["include"])).lower(),
        "smoke_standard_matrix": json.dumps(smoke_standard_matrix),
        "smoke_heavy_matrix": json.dumps(smoke_heavy_matrix),
        "integration_standard_matrix": json.dumps(integration_standard_matrix),
        "integration_heavy_matrix": json.dumps(integration_heavy_matrix),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed_files = git_changed_files(args.base_sha, args.head_sha, repo_root=REPO_ROOT)
    outputs = build_outputs_for_changed_files(changed_files, repo_root=REPO_ROOT)
    if args.github_output:
        write_github_outputs(outputs, args.github_output)
    else:
        print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
