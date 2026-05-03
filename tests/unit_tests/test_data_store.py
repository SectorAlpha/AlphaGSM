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
