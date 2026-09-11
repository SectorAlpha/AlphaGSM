"""CLI mutations acquire ownership before loading a server datastore."""
from contextlib import contextmanager
from importlib import import_module


def test_run_one_locks_before_loading_server(monkeypatch, tmp_path):
    module = import_module("core.main")
    events = []

    @contextmanager
    def lock(path):
        events.append(("lock", str(path)))
        yield
        events.append(("unlock", str(path)))

    monkeypatch.setattr(module.servermodule, "DATAPATH", str(tmp_path))
    monkeypatch.setattr("utils.state_io.state_lock", lock)
    monkeypatch.setattr(module, "_run_one_unlocked", lambda *args: events.append(("run", "")) or 0,
                        raising=False)
    assert module.run_one("alphagsm", (None, "demo"), "set", ["port", "12345"]) == 0
    assert [event[0] for event in events] == ["lock", "run", "unlock"]


def test_invalid_local_tag_cannot_create_lock_outside_datapath(tmp_path, monkeypatch):
    module = import_module("core.main")
    monkeypatch.setattr(module.servermodule, "DATAPATH", str(tmp_path))
    assert module.run_one("alphagsm", (None, "../outside"), "set", []) == 2
    assert not (tmp_path.parent / "outside.json.lock").exists()


def test_server_wildcard_excludes_secret_sidecars(tmp_path, monkeypatch):
    module = import_module("core.main")
    for name in ("demo.json", "demo.secrets.json", "demo.json.pending", "demo.json.lock"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / ".provenance").mkdir()
    monkeypatch.setattr(module.servermodule, "DATAPATH", str(tmp_path))
    assert module.get_all_user_servers() == [(None, "demo")]
