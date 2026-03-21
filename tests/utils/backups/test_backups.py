import datetime
import subprocess as sp

import pytest

import utils.backups.backups as backups_module


def sample_config():
    return {
        "profiles": {
            "base": {"targets": ["world"], "exclusions": ["*.tmp"]},
            "child": {"base": "base", "targets": ["ops.json"], "lifetime": (1, "day")},
        },
        "schedule": [("child", 1, "day"), ("base", 0, "day")],
    }


def test_getprofiledata_merges_base_profile():
    profile = backups_module.getprofiledata(sample_config(), "child")

    assert profile["targets"] == ["world", "ops.json"]
    assert profile["exclusions"] == ["*.tmp"]
    assert profile["lifetime"] == (1, "day")


def test_getprofiledata_raises_for_unknown_profile():
    with pytest.raises(backups_module.BackupError, match="Unknown backup profile"):
        backups_module.getprofiledata(sample_config(), "missing")


def test_applydelta_supports_year_month_week_and_day(capsys):
    ts = datetime.datetime(2024, 1, 31, 12, 0, 0)

    assert backups_module.applydelta(ts, 1, "year") == datetime.datetime(2025, 1, 31, 12, 0, 0)
    assert backups_module.applydelta(ts, 1, "month") == datetime.datetime(2024, 2, 29, 12, 0, 0)
    assert backups_module.applydelta(ts, 1, "week") == datetime.datetime(2024, 2, 7, 12, 0, 0)
    assert backups_module.applydelta(ts, 1, "day") == datetime.datetime(2024, 2, 1, 12, 0, 0)
    assert backups_module.applydelta(ts, 1, "mystery") == ts
    assert "Unknown time unit" in capsys.readouterr().out


def test_doschedule_selects_first_due_profile():
    now = datetime.datetime(2024, 1, 10, 12, 0, 0)
    backups = {
        "child": [("child old.zip", now - datetime.timedelta(days=2))],
        "base": [("base recent.zip", now)],
    }

    assert backups_module.doschedule(sample_config(), now, backups) == "child"


def test_doschedule_requires_non_empty_schedule():
    with pytest.raises(backups_module.BackupError, match="No schedule defined"):
        backups_module.doschedule({"schedule": []}, datetime.datetime.utcnow(), {})


def test_backup_creates_zip_command_and_prunes_old_files(tmp_path, monkeypatch):
    monkeypatch.setattr(backups_module, "BACKUPDIR", "backup")
    now = datetime.datetime(2024, 1, 10, 12, 0, 0)
    monkeypatch.setattr(backups_module.datetime, "datetime", type("FakeDatetime", (), {
        "utcnow": staticmethod(lambda: now),
        "strptime": staticmethod(datetime.datetime.strptime),
    }))
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    old_name = "child 2024.01.08 12:00:00.000000.zip"
    keep_name = "child 2024.01.10 11:00:00.000000.zip"
    (backup_dir / old_name).write_text("old")
    (backup_dir / keep_name).write_text("keep")
    calls = []
    removed = []

    monkeypatch.setattr(backups_module.sp, "check_call", lambda cmd, cwd=None: calls.append((cmd, cwd)))
    monkeypatch.setattr(backups_module.os, "remove", lambda path: removed.append(path))

    backups_module.backup(str(tmp_path), sample_config(), profile="child")

    assert calls
    assert calls[0][0][:3] == ["zip", "-ry", "backup/child 2024.01.10 12:00:00.000000.zip"]
    assert calls[0][1] == str(tmp_path)
    assert str(backup_dir / old_name) in removed
    assert str(backup_dir / keep_name) not in removed


def test_backup_returns_cleanly_when_zip_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(backups_module, "BACKUPDIR", "backup")
    (tmp_path / "backup").mkdir()
    monkeypatch.setattr(backups_module.sp, "check_call", lambda cmd, cwd=None: (_ for _ in ()).throw(sp.CalledProcessError(1, cmd)))

    backups_module.backup(str(tmp_path), sample_config(), profile="child")

    assert "Error backing up the server" in capsys.readouterr().out


def test_checkdatavalue_validates_profile_and_schedule_entries():
    data = {"profiles": {"base": {}}, "schedule": []}

    assert backups_module.checkdatavalue(data, ("profiles", "base"), "DELETE") == "DELETE"
    assert backups_module.checkdatavalue(data, ("profiles", "base", "targets"), "world", "ops.json") == ["world", "ops.json"]
    assert backups_module.checkdatavalue(data, ("profiles", "base", "replace_targets"), "yes") is True
    assert backups_module.checkdatavalue(data, ("profiles", "base", "replace_targets"), "off") is False
    assert backups_module.checkdatavalue(data, ("profiles", "base", "lifetime"), "2", "week") == [2, "week"]
    assert backups_module.checkdatavalue(data, ("schedule", "0"), "base", "1", "day") == ["base", 1, "day"]


def test_checkdatavalue_rejects_invalid_values():
    data = {"profiles": {"base": {}}, "schedule": []}

    with pytest.raises(backups_module.BackupError, match="Invalid backup profile name"):
        backups_module.checkdatavalue(data, ("profiles", "bad-name", "targets"), "x")
    with pytest.raises(backups_module.BackupError, match="Only boolean values allowed"):
        backups_module.checkdatavalue(data, ("profiles", "base", "replace_targets"), "maybe")
    with pytest.raises(backups_module.BackupError, match="Profile base must be a valid profile"):
        backups_module.checkdatavalue(data, ("profiles", "base", "base"), "missing")
    with pytest.raises(backups_module.BackupError, match="valid time unit"):
        backups_module.checkdatavalue(data, ("schedule", "0"), "base", "1", "hour")
    with pytest.raises(backups_module.BackupError, match="Invalid key"):
        backups_module.checkdatavalue(data, ("unknown",), "x")
