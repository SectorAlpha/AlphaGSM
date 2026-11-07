"""Cached L4D2 test depots must retain the engine's startup configuration."""

import importlib.util
from pathlib import Path
import sys

import pytest


def test_cached_depots_preserve_stock_configs_and_exclude_generated_state(tmp_path, monkeypatch):
    from tests.integration_tests import conftest as helpers
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    source = Path(__file__).parents[1] / "integration_tests" / "test_l4d2server.py"
    spec = importlib.util.spec_from_file_location("_l4d2_cache_contract", source)
    integration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(integration)
    cache = tmp_path / "cache"
    files = {
        "srcds_run": "engine launcher",
        "left4dead2/cfg/valve.rc": "exec autoexec.cfg\nstuffcmds\n",
        "left4dead2/cfg/360controller.cfg": "stock input settings",
        "left4dead2/cfg/server.cfg": "hostname operator settings",
        "left4dead2/addons/workshop/123.vpk": "old addon payload",
        ".alphagsm/workshop/content/550/123/addon.vpk": "old manager state",
    }
    for relative, text in files.items():
        path = cache / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.setenv("ALPHAGSM_L4D2_TEST_CACHE", str(cache))
    for name in ("require_integration_opt_in", "require_steamcmd_opt_in", "require_command_for_runtime"):
        monkeypatch.setattr(integration, name, lambda *_args, **_kwargs: None)

    def stop_before_commands(*_args, **_kwargs):
        raise RuntimeError("stop before AlphaGSM commands")

    monkeypatch.setattr(integration, "write_config", stop_before_commands)
    case = tmp_path / "case"
    case.mkdir()
    with pytest.raises(RuntimeError, match="stop before AlphaGSM commands"):
        integration.test_l4d2server_lifecycle(case, runtime_backend="process")
    install = case / "server"
    for relative in ("srcds_run", "left4dead2/cfg/valve.rc", "left4dead2/cfg/360controller.cfg"):
        assert (install / relative).read_text(encoding="utf-8") == files[relative]
    assert not (install / "left4dead2/cfg/server.cfg").exists()
    assert not (install / "left4dead2/addons").exists()
    assert not (install / ".alphagsm").exists()
