from scripts.generate_game_server_support_tracker import (
    SupportTrackerValidationError,
    parse_summary_counts,
    parse_status_sections,
    render_support_tracker,
    validate_support_tracker_state,
)


def test_parse_status_sections_includes_enabled_byo():
    text = """
## PASSED (1)
| Test | Type |
|------|------|
| acserver | SteamCMD |

## ENABLED (BYO) (2)
| Test | Type |
|------|------|
| cod2server | bring-your-own-assets |
| dstserver | bring-your-own-config |

## DISABLED (1)
| Test | Reason |
|------|--------|
| bfvserver | dead URL |

## SKIPPED (1)
| Test | Skip reason |
|------|-------------|
| stormworksserver | redirected |
"""
    rows = parse_status_sections(text)
    assert rows["PASSED"] == ["acserver"]
    assert rows["ENABLED (BYO)"] == ["cod2server", "dstserver"]
    assert rows["DISABLED"] == ["bfvserver"]
    assert rows["SKIPPED"] == ["stormworksserver"]


def test_parse_status_sections_includes_enabled_auth():
    text = """
## PASSED (1)
| Test | Type |
|------|------|
| acserver | SteamCMD |

## ENABLED (AUTH) (1)
| Test | Type |
|------|------|
| tiserver | eos credentials |
"""
    rows = parse_status_sections(text)
    assert rows["ENABLED (AUTH)"] == ["tiserver"]


def test_parse_summary_counts_reads_summary_table():
    text = """
## Summary

| Status | Count |
|--------|-------|
| PASSED | 146 |
| ENABLED (AUTH) | 47 |
| ENABLED (BYO) | 41 |
| DISABLED | 3 |
| SKIPPED | 0 |
"""
    assert parse_summary_counts(text) == {
        "PASSED": 146,
        "ENABLED (AUTH)": 47,
        "ENABLED (BYO)": 41,
        "DISABLED": 3,
        "SKIPPED": 0,
    }


def test_render_support_tracker_counts_enabled_byo_as_supported():
    rows = {
        "PASSED": ["acserver"],
        "ENABLED (AUTH)": ["tiserver"],
        "ENABLED (BYO)": ["cod2server"],
        "DISABLED": ["bfvserver"],
        "SKIPPED": ["stormworksserver"],
    }
    rendered = render_support_tracker(rows)
    assert "## Supported Now" in rendered
    assert "- [x] acserver" in rendered
    assert "- [x] tiserver" in rendered
    assert "- [x] cod2server" in rendered
    assert "- [ ] bfvserver" in rendered
    assert "- [ ] stormworksserver" in rendered


def test_validate_support_tracker_state_accepts_namespaced_module_rows(tmp_path):
    repo_root = tmp_path
    docs_dir = repo_root / "docs"
    docs_dir.mkdir()

    (docs_dir / "TEST_STATUS.md").write_text(
        """
## Summary

| Status | Count |
|--------|-------|
| PASSED | 0 |
| ENABLED (AUTH) | 1 |
| ENABLED (BYO) | 2 |
| DISABLED | 1 |
| SKIPPED | 0 |

## PASSED (0)
| Test | Type |
|------|------|

## ENABLED (AUTH) (1)
| Test | Type |
|------|------|
| arma3_altislife | authenticated install |

## ENABLED (BYO) (2)
| Test | Type |
|------|------|
| minecraft_custom | staged jar |
| minecraft_tekkit | staged Tekkit.jar |

## DISABLED (1)
| Test | Reason |
|------|--------|
| counterstrikeglobaloffensive | stale upstream |

## SKIPPED (0)
| Test | Skip reason |
|------|-------------|
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (docs_dir / "game-server-support.md").write_text(
        render_support_tracker(
            parse_status_sections((docs_dir / "TEST_STATUS.md").read_text(encoding="utf-8"))
        ),
        encoding="utf-8",
    )
    (repo_root / "disabled_servers.conf").write_text(
        "counterstrikeglobaloffensive\tstale upstream\n",
        encoding="utf-8",
    )
    (repo_root / "enabled_byo_servers.conf").write_text(
        "minecraft.custom\turl\tstaged jar\n"
        "minecraft.tekkit\turl\tstaged Tekkit.jar\n",
        encoding="utf-8",
    )
    (repo_root / "enabled_auth_servers.conf").write_text(
        "arma3.altislife\tprovider-license\tauthenticated install\n",
        encoding="utf-8",
    )

    validate_support_tracker_state(repo_root)


def test_validate_support_tracker_state_rejects_missing_tracker_rows(tmp_path):
    repo_root = tmp_path
    docs_dir = repo_root / "docs"
    docs_dir.mkdir()

    (docs_dir / "TEST_STATUS.md").write_text(
        """
## Summary

| Status | Count |
|--------|-------|
| PASSED | 0 |
| ENABLED (AUTH) | 0 |
| ENABLED (BYO) | 0 |
| DISABLED | 1 |
| SKIPPED | 0 |

## PASSED (0)
| Test | Type |
|------|------|

## ENABLED (AUTH) (0)
| Test | Type |
|------|------|

## ENABLED (BYO) (0)
| Test | Type |
|------|------|

## DISABLED (1)
| Test | Reason |
|------|--------|
| counterstrikeglobaloffensive | stale upstream |

## SKIPPED (0)
| Test | Skip reason |
|------|-------------|
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (docs_dir / "game-server-support.md").write_text(
        render_support_tracker(
            parse_status_sections((docs_dir / "TEST_STATUS.md").read_text(encoding="utf-8"))
        ),
        encoding="utf-8",
    )
    (repo_root / "disabled_servers.conf").write_text(
        "counterstrikeglobaloffensive\tstale upstream\n"
        "abfserver\tinvalid platform\n",
        encoding="utf-8",
    )
    (repo_root / "enabled_byo_servers.conf").write_text("", encoding="utf-8")
    (repo_root / "enabled_auth_servers.conf").write_text("", encoding="utf-8")

    try:
        validate_support_tracker_state(repo_root)
    except SupportTrackerValidationError as exc:
        assert "DISABLED mismatch" in str(exc)
        assert "abfserver" in str(exc)
    else:
        raise AssertionError("expected SupportTrackerValidationError")


def test_validate_support_tracker_state_rejects_enabled_disabled_overlap(tmp_path):
    repo_root = tmp_path
    docs_dir = repo_root / "docs"
    docs_dir.mkdir()

    (docs_dir / "TEST_STATUS.md").write_text(
        """
## Summary

| Status | Count |
|--------|-------|
| PASSED | 0 |
| ENABLED (AUTH) | 0 |
| ENABLED (BYO) | 1 |
| DISABLED | 1 |
| SKIPPED | 0 |

## PASSED (0)
| Test | Type |
|------|------|

## ENABLED (AUTH) (0)
| Test | Type |
|------|------|

## ENABLED (BYO) (1)
| Test | Type |
|------|------|
| minecraft_tekkit | staged Tekkit.jar |

## DISABLED (1)
| Test | Reason |
|------|--------|
| minecraft_tekkit | stale upstream |

## SKIPPED (0)
| Test | Skip reason |
|------|-------------|
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (docs_dir / "game-server-support.md").write_text(
        render_support_tracker(
            parse_status_sections((docs_dir / "TEST_STATUS.md").read_text(encoding="utf-8"))
        ),
        encoding="utf-8",
    )
    (repo_root / "disabled_servers.conf").write_text(
        "minecraft.tekkit\tstale upstream\n",
        encoding="utf-8",
    )
    (repo_root / "enabled_byo_servers.conf").write_text(
        "minecraft.tekkit\turl\tstaged Tekkit.jar\n",
        encoding="utf-8",
    )
    (repo_root / "enabled_auth_servers.conf").write_text("", encoding="utf-8")

    try:
        validate_support_tracker_state(repo_root)
    except SupportTrackerValidationError as exc:
        assert "listed in both disabled and enabled gate files" in str(exc)
        assert "minecraft.tekkit" in str(exc)
    else:
        raise AssertionError("expected SupportTrackerValidationError")


def test_validate_support_tracker_state_rejects_summary_count_drift(tmp_path):
    repo_root = tmp_path
    docs_dir = repo_root / "docs"
    docs_dir.mkdir()

    (docs_dir / "TEST_STATUS.md").write_text(
        """
## Summary

| Status | Count |
|--------|-------|
| PASSED | 2 |
| ENABLED (AUTH) | 0 |
| ENABLED (BYO) | 0 |
| DISABLED | 1 |
| SKIPPED | 0 |

## PASSED (1)
| Test | Type |
|------|------|
| acserver | SteamCMD |

## ENABLED (AUTH) (0)
| Test | Type |
|------|------|

## ENABLED (BYO) (0)
| Test | Type |
|------|------|

## DISABLED (1)
| Test | Reason |
|------|--------|
| counterstrikeglobaloffensive | stale upstream |

## SKIPPED (0)
| Test | Skip reason |
|------|-------------|
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (docs_dir / "game-server-support.md").write_text(
        render_support_tracker(
            parse_status_sections((docs_dir / "TEST_STATUS.md").read_text(encoding="utf-8"))
        ),
        encoding="utf-8",
    )
    (repo_root / "disabled_servers.conf").write_text(
        "counterstrikeglobaloffensive\tstale upstream\n",
        encoding="utf-8",
    )
    (repo_root / "enabled_byo_servers.conf").write_text("", encoding="utf-8")
    (repo_root / "enabled_auth_servers.conf").write_text("", encoding="utf-8")

    try:
        validate_support_tracker_state(repo_root)
    except SupportTrackerValidationError as exc:
        assert "Summary count mismatch" in str(exc)
        assert "PASSED" in str(exc)
    else:
        raise AssertionError("expected SupportTrackerValidationError")
