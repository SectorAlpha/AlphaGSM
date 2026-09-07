import json
import os
import stat

import pytest

from tests.helpers import load_module_from_repo


data_module = load_module_from_repo("server_data_module", "src/server/data.py")
DataError = data_module.DataError
JSONDataStore = data_module.JSONDataStore


def test_json_data_store_uses_provided_dict_without_loading(tmp_path):
    store = JSONDataStore(str(tmp_path / "unused.json"), {"a": 1})

    assert len(store) == 1
    assert store["a"] == 1
    assert "a" in store
    assert list(store) == ["a"]


def test_json_data_store_loads_and_saves_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"name": "alpha"}))

    store = JSONDataStore(str(path))
    store["count"] = 2
    store.save()

    saved = json.loads(path.read_text())
    assert saved == {"name": "alpha", "count": 2}


def test_json_data_store_missing_file_raises_data_error(tmp_path):
    with pytest.raises(DataError):
        JSONDataStore(str(tmp_path / "missing.json"))


def test_json_data_store_mapping_helpers(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"name": "alpha"}))
    store = JSONDataStore(str(path))

    assert store.get("missing", "fallback") == "fallback"
    assert store.setdefault("name", "beta") == "alpha"
    assert store.setdefault("mode", "test") == "test"

    del store["mode"]

    assert "mode" not in store


def test_json_data_store_prettydump_is_sorted_and_indented(tmp_path):
    store = JSONDataStore(str(tmp_path / "data.json"), {"b": 2, "a": 1})

    assert store.prettydump() == '{\n  "a": 1,\n  "b": 2\n}'


# --- secret-key split tests ---


def test_save_with_secret_keys_splits_files(tmp_path):
    path = tmp_path / "data.json"
    secrets_path = tmp_path / "data.secrets.json"
    store = JSONDataStore(
        str(path), {"port": 27015, "rconpassword": "s3cr3t", "servername": "MyServer"}
    )
    store.set_secret_keys({"rconpassword"}, str(secrets_path))
    store.save()

    main = json.loads(path.read_text())
    assert "rconpassword" not in main
    assert main["port"] == 27015
    assert main["servername"] == "MyServer"

    assert secrets_path.exists()
    secrets = json.loads(secrets_path.read_text())
    assert secrets == {"rconpassword": "s3cr3t"}


def test_secrets_file_has_restricted_permissions(tmp_path):
    store = JSONDataStore(str(tmp_path / "data.json"), {"rconpassword": "s3cr3t"})
    secrets_path = tmp_path / "data.secrets.json"
    store.set_secret_keys({"rconpassword"}, str(secrets_path))
    store.save()

    file_mode = stat.S_IMODE(os.stat(str(secrets_path)).st_mode)
    assert file_mode == 0o600


def test_set_secret_keys_merges_existing_secrets_file(tmp_path):
    secrets_path = tmp_path / "data.secrets.json"
    secrets_path.write_text(json.dumps({"rconpassword": "from_file"}))

    store = JSONDataStore(str(tmp_path / "data.json"), {"port": 27015})
    store.set_secret_keys({"rconpassword"}, str(secrets_path))

    assert store["rconpassword"] == "from_file"
    assert store["port"] == 27015


def test_migration_secret_key_in_main_file(tmp_path):
    path = tmp_path / "data.json"
    secrets_path = tmp_path / "data.secrets.json"
    path.write_text(json.dumps({"port": 27015, "rconpassword": "migrate_me"}))

    store = JSONDataStore(str(path))
    store.set_secret_keys({"rconpassword"}, str(secrets_path))
    store.save()

    main = json.loads(path.read_text())
    assert "rconpassword" not in main
    assert main["port"] == 27015

    secrets = json.loads(secrets_path.read_text())
    assert secrets["rconpassword"] == "migrate_me"


def test_prettydump_redacts_non_empty_secret_values(tmp_path):
    store = JSONDataStore(
        str(tmp_path / "data.json"), {"port": 27015, "rconpassword": "s3cr3t"}
    )
    store.set_secret_keys({"rconpassword"}, str(tmp_path / "data.secrets.json"))

    parsed = json.loads(store.prettydump())
    assert parsed["rconpassword"] == "<redacted>"
    assert parsed["port"] == 27015


def test_prettydump_does_not_redact_empty_secret_value(tmp_path):
    store = JSONDataStore(str(tmp_path / "data.json"), {"rconpassword": ""})
    store.set_secret_keys({"rconpassword"}, str(tmp_path / "data.secrets.json"))

    parsed = json.loads(store.prettydump())
    assert parsed["rconpassword"] == ""


def test_save_without_secret_keys_is_unchanged(tmp_path):
    path = tmp_path / "data.json"
    store = JSONDataStore(str(path), {"port": 27015, "name": "srv"})
    store.save()

    saved = json.loads(path.read_text())
    assert saved == {"port": 27015, "name": "srv"}
    assert not (tmp_path / "data.secrets.json").exists()


def test_failed_json_serialization_preserves_original(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('{"old": true}')
    store = JSONDataStore(str(path))
    store["bad"] = object()
    with pytest.raises(TypeError):
        store.save()
    assert json.loads(path.read_text()) == {"old": True}


def test_transaction_reloads_stale_store_before_mutating(tmp_path):
    path = tmp_path / "data.json"
    first = JSONDataStore(str(path), {"count": 0})
    first.save()
    stale = JSONDataStore(str(path))
    with first.transaction():
        first["count"] += 1
    with stale.transaction():
        stale["count"] += 1
    assert JSONDataStore(str(path))["count"] == 2


def test_nested_transaction_does_not_reload_outer_changes(tmp_path):
    path = tmp_path / "data.json"
    store = JSONDataStore(str(path), {"count": 0})
    store.save()
    with store.transaction():
        store["count"] = 1
        with store.transaction():
            store["other"] = 2
        assert store["count"] == 1
    assert dict(JSONDataStore(str(path))) == {"count": 1, "other": 2}


def test_failed_transaction_does_not_save_mutations(tmp_path):
    path = tmp_path / "data.json"
    store = JSONDataStore(str(path), {"nested": {"value": 1}})
    store.save()
    with pytest.raises(RuntimeError):
        with store.transaction():
            store["nested"]["value"] = 2
            raise RuntimeError("abort")
    assert store["nested"]["value"] == 1
    assert JSONDataStore(str(path))["nested"]["value"] == 1


def test_interrupted_secret_pair_recovers_complete_new_state(monkeypatch, tmp_path):
    from utils import state_io

    path = tmp_path / "data.json"
    secrets = tmp_path / "data.secrets.json"
    store = JSONDataStore(str(path), {"port": 1, "password": "old"})
    store.set_secret_keys({"password"}, str(secrets))
    store.save()
    store["port"] = 2
    store["password"] = "new"
    replace = state_io.os.replace

    def fail_main(source, target):
        if os.fspath(target) == str(path):
            raise PermissionError("main write interrupted")
        return replace(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(state_io.os, "replace", fail_main)
        with pytest.raises(PermissionError):
            store.save()
    recovered = JSONDataStore(str(path))
    recovered.set_secret_keys({"password"}, str(secrets))
    assert dict(recovered) == {"port": 2, "password": "new"}
    assert "password" not in json.loads(path.read_text())
    assert not (tmp_path / "data.json.pending").exists()


def test_load_reloads_current_secrets(tmp_path):
    path = tmp_path / "data.json"
    secrets = tmp_path / "data.secrets.json"
    store = JSONDataStore(str(path), {"password": "old"})
    store.set_secret_keys({"password"}, str(secrets))
    store.save()
    secrets.write_text('{"password": "new"}')
    store.load()
    assert store["password"] == "new"


def test_secret_file_cannot_alias_main_file(tmp_path):
    path = tmp_path / "data.json"
    store = JSONDataStore(str(path), {"password": "secret"})
    with pytest.raises(DataError, match="distinct"):
        store.set_secret_keys({"password"}, str(path))
    assert not (tmp_path / "data.json.pending").exists()


def test_secret_file_cannot_replace_the_active_lock_inode(tmp_path):
    path = tmp_path / "data.json"
    store = JSONDataStore(str(path), {"password": "secret"})
    with pytest.raises(DataError, match="distinct"):
        store.set_secret_keys({"password"}, str(path) + ".lock")


def test_pending_journal_cannot_replace_the_active_lock_inode(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('{"port": 1}')
    pending = tmp_path / "data.json.pending"
    pending.write_text(json.dumps({
        "main": {"port": 2}, "secrets": {"password": "secret"},
        "secrets_filename": "data.json.lock",
    }))
    with pytest.raises(DataError, match="Invalid pending"):
        JSONDataStore(str(path))
    assert json.loads(path.read_text()) == {"port": 1}


def test_transactions_serialize_process_updates(tmp_path):
    import subprocess
    import sys

    path = tmp_path / "data.json"
    JSONDataStore(str(path), {"count": 0}).save()
    script = '''
from server.data import JSONDataStore
import sys
store = JSONDataStore(sys.argv[1])
for _ in range(15):
    with store.transaction():
        store['count'] += 1
'''
    processes = [subprocess.Popen([sys.executable, "-c", script, str(path)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for _ in range(3)]
    for process in processes:
        _out, error = process.communicate(timeout=20)
        assert process.returncode == 0, error
    assert JSONDataStore(str(path))["count"] == 45
