import json

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
