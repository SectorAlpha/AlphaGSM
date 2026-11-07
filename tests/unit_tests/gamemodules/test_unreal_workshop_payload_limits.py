"""Unreal adapters stop oversized payload enumeration before staging."""
# pylint: disable=protected-access
from importlib import import_module
from pathlib import Path

import pytest

from server import ServerError


@pytest.mark.parametrize("name", ["conanexiles", "ark", "squadserver"])
def test_payload_limit_stops_enumeration_without_consuming_unbounded_tree(name, tmp_path, monkeypatch):
    """A malformed oversized tree must fail at its boundary, before native writes."""
    module = import_module(f"gamemodules.{name}.workshop")
    payload = tmp_path / "payload"
    payload.mkdir()
    def oversized(_path, _pattern):
        for index in range(10001):
            yield payload / f"{index}.asset"
        raise AssertionError("adapter consumed the unbounded remainder of the payload")
    monkeypatch.setattr(Path, "rglob", oversized)
    with pytest.raises(ServerError):
        if name == "conanexiles":
            module._pak_files({"111": payload})
        elif name == "ark":
            module._prepare_files({"111": payload}, tmp_path / "scratch")
        else:
            module._plugin_files({"111": payload}, "SquadGame")
    assert not (tmp_path / "scratch").exists()
