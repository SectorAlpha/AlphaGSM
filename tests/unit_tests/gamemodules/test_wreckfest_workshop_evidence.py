"""Wreckfest Workshop proof requires a bounded native track-registry response."""

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.smoke_tests import wreckfestserver_workshop as module
from tests.smoke_tests.wreckfestserver_workshop import (
    assert_workshop_loaded, wait_for_workshop_loaded,
)


def test_native_tracks_section_accepts_exact_event_with_display_name():
    assert_workshop_loaded(
        "Server connected.\r\nTracks:\r\n"
        "  bigstadium_demolition_arena (MADMAN STADIUM - DEMOLITION ARENA)\r\n"
        "  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\r\n"
        "  crazy_2000_reversed (CRAZY 2000 - CRAZY 2000 REVERSED)\r\n"
        "Server running.\r\n")


@pytest.mark.parametrize("text", [
    "tracks\nconfig track=crazy_2000_classic",
    "  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n",
    "command line: Tracks: crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n",
    "Tracks:\n  track=crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n",
    "Tracks:\n  crazy_2000_classic\n",
    "Tracks:\n  crazy_2000_classic ()\n",
    "Tracks:\n  crazy_2000_classic_extra (CRAZY 2000 - CRAZY 2000)\n",
    "Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000) config echo\n",
    "Tracks:\n  bigstadium_figure_8 (MADMAN STADIUM - FIGURE 8)\n"
    "Configuration:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n",
    "Tracks:\n  bigstadium_figure_8 (MADMAN STADIUM - FIGURE 8)\n\n"
    "  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n",
])
def test_non_registry_echo_or_unsectioned_event_is_not_load_proof(text):
    with pytest.raises(AssertionError):
        assert_workshop_loaded(text)


def test_previous_registry_cannot_satisfy_latest_tracks_response():
    with pytest.raises(AssertionError):
        assert_workshop_loaded(
            "Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n"
            "Server restarted.\nTracks:\n  bigstadium_figure_8 (MADMAN STADIUM - FIGURE 8)\n")


@pytest.mark.parametrize("failure", ["Unknown command: tracks", "Error: tracks unavailable",
                                      "Failed to load crazy_2000_classic", "crazy_2000_classic not found"])
def test_engine_command_or_load_error_invalidates_registry_evidence(failure):
    with pytest.raises(AssertionError):
        assert_workshop_loaded(
            "Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n" + failure)


def test_oversized_capture_cannot_satisfy_bounded_response_contract():
    with pytest.raises(AssertionError):
        assert_workshop_loaded("x" * (1024 * 1024) +
                               "\nTracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n")


def test_event_after_registry_row_bound_is_not_load_proof():
    with pytest.raises(AssertionError):
        assert_workshop_loaded("Tracks:\n" + "  stock_track (STOCK TRACK)\n" * 1024 +
                               "  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n")


def test_poller_waits_for_complete_registry_instead_of_config_substring():
    outputs = iter(["tracks\nconfig track=crazy_2000_classic",
                    "Tracks:\n  crazy_2000_classic",
                    "Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n"])
    elapsed = [0.0]
    budgets = []

    def fetch(remaining):
        budgets.append(remaining)
        elapsed[0] += 0.25
        return next(outputs)

    def pause(seconds):
        elapsed[0] += seconds

    result = wait_for_workshop_loaded(fetch, timeout_seconds=5,
                                      clock=lambda: elapsed[0], sleep=pause)
    assert result == "Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n"
    assert budgets == [5, 3.75, 2.5]


def test_poller_times_out_with_last_parser_reason_and_remaining_fetch_budget():
    elapsed = [0.0]
    budgets = []

    def fetch(remaining):
        budgets.append(remaining)
        elapsed[0] += min(0.5, remaining)
        return "tracks\nconfig track=crazy_2000_classic"

    def pause(seconds):
        elapsed[0] += seconds

    with pytest.raises(AssertionError, match="Timed out.*Tracks: registry section is missing"):
        wait_for_workshop_loaded(fetch, timeout_seconds=2,
                                 clock=lambda: elapsed[0], sleep=pause)
    assert budgets == [2, 0.5]
    assert elapsed[0] == 2


def test_poller_does_not_accept_valid_output_returned_after_deadline():
    elapsed = [0.0]

    def fetch(remaining):
        assert remaining == 1
        elapsed[0] += 2
        return "Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n"

    with pytest.raises(AssertionError, match="Timed out"):
        wait_for_workshop_loaded(fetch, timeout_seconds=1,
                                 clock=lambda: elapsed[0], sleep=lambda _seconds: None)


def test_cli_server_mode_fetches_bounded_alphagsm_logs_then_writes_evidence(tmp_path, monkeypatch):
    evidence = tmp_path / "fresh-native-registry.log"
    calls = []
    native = "Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n"

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout=native)

    monkeypatch.setattr(sys, "argv", ["workshop", str(evidence), "--server", "itwreck", "--timeout", "4"])
    monkeypatch.setattr(module.subprocess, "run", run)
    module.main()
    command, options = calls[0]
    assert command == [sys.executable, str(Path(module.__file__).resolve().parents[2] / "alphagsm"),
                       "itwreck", "logs", "-n", "2000"]
    assert 0 < options["timeout"] <= 4
    assert options["capture_output"] and options["text"] and options["check"]
    assert evidence.read_text(encoding="utf-8") == native


def test_cli_failed_log_command_does_not_replace_evidence(tmp_path, monkeypatch):
    evidence = tmp_path / "native-registry.log"
    evidence.write_text("previous evidence", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["workshop", str(evidence), "--server", "itwreck"])

    def fail(command, **_kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(module.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        module.main()
    assert evidence.read_text(encoding="utf-8") == "previous evidence"


def test_cli_plain_log_mode_retains_parser_without_fetching(tmp_path, monkeypatch):
    evidence = tmp_path / "native-registry.log"
    evidence.write_text("Tracks:\n  crazy_2000_classic (CRAZY 2000 - CRAZY 2000)\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["workshop", str(evidence)])

    def unexpected_fetch(*_args, **_kwargs):
        raise AssertionError("Plain log mode must not execute AlphaGSM")

    monkeypatch.setattr(module.subprocess, "run", unexpected_fetch)
    module.main()
