"""Tests for stable CI port allocation outside the OS ephemeral range."""

from pathlib import Path

import pytest

from scripts import select_test_port


def test_candidate_base_ports_exclude_groups_overlapping_ephemeral_range():
    candidates = select_test_port.candidate_base_ports(
        2,
        min_port=32766,
        max_port=61002,
        ephemeral_range=(32768, 60999),
    )

    assert candidates == [32766, 61000, 61001]


def test_default_candidates_stay_in_dedicated_test_port_range():
    candidates = select_test_port.candidate_base_ports(
        1,
        ephemeral_range=(32768, 60999),
    )

    assert candidates[0] == 10000
    assert candidates[-1] == 29999


def test_pick_free_port_group_checks_every_port_in_selected_group():
    checked = []

    def port_is_free(port):
        checked.append(port)
        return port in {61000, 61001}

    port = select_test_port.pick_free_port_group(
        2,
        min_port=32766,
        max_port=61002,
        ephemeral_range=(32768, 60999),
        start_index=1,
        port_is_free=port_is_free,
    )

    assert port == 61000
    assert checked == [61000, 61001]


def test_read_ephemeral_port_range_uses_linux_kernel_values(tmp_path):
    range_path = tmp_path / "ip_local_port_range"
    range_path.write_text("40000 49999\n", encoding="ascii")

    assert select_test_port.read_ephemeral_port_range(range_path) == (40000, 49999)


def test_read_ephemeral_port_range_falls_back_for_invalid_content(tmp_path):
    range_path = tmp_path / "ip_local_port_range"
    range_path.write_text("not-a-range\n", encoding="ascii")

    assert select_test_port.read_ephemeral_port_range(range_path) == (
        select_test_port.DEFAULT_EPHEMERAL_MIN,
        select_test_port.DEFAULT_EPHEMERAL_MAX,
    )


def test_pick_free_port_group_rejects_invalid_count():
    with pytest.raises(ValueError, match="positive"):
        select_test_port.pick_free_port_group(0)


def test_main_prints_selected_group_base(monkeypatch, capsys):
    monkeypatch.setattr(
        select_test_port,
        "pick_free_port_group",
        lambda count: 24567 if count == 3 else None,
    )

    assert select_test_port.main(["3"]) == 0
    assert capsys.readouterr().out == "24567\n"


def test_smoke_helpers_delegate_port_selection_to_shared_script():
    helpers = (
        Path(__file__).resolve().parents[1]
        / "smoke_tests"
        / "steamcmd_helpers.sh"
    ).read_text(encoding="utf-8")

    assert "scripts/select_test_port.py" in helpers
    assert 'pick_free_port_group 1' in helpers


def test_python_integration_helpers_delegate_to_shared_selector():
    tests_root = Path(__file__).resolve().parents[1]
    integration_helpers = (
        tests_root / "integration_tests" / "conftest.py"
    ).read_text(encoding="utf-8")
    backend_helpers = (
        tests_root / "backend_integration_tests" / "conftest.py"
    ).read_text(encoding="utf-8")

    assert "from scripts import select_test_port" in integration_helpers
    assert "from scripts import select_test_port" in backend_helpers
