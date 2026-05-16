"""Shared fixtures for the AlphaGSM unit test suite.

This conftest is intentionally self-contained so that ``pytest tests/unit_tests``
works without needing the parent ``tests/conftest.py`` to be loaded first.
"""

import os
import re
import sys
import urllib.request
from pathlib import Path

import pytest

# Ensure src/ is on the path so game modules etc. are importable when pytest
# is invoked directly as ``pytest tests/unit_tests`` without PYTHONPATH=.:src.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_src = str(_REPO_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

os.environ["ALPHAGSM_CONFIG_LOCATION"] = str(_REPO_ROOT / "tests" / "alphagsm-test.conf")

_GAMEMODULE_POP_RE = re.compile(r"sys\.modules\.pop\('gamemodules\.([^']+)'")


def _clear_cached_package_main_modules(test_file):
    """Reset cached package-backed module impls before importing a test module.

    Many generated coverage tests still clear only ``gamemodules.<name>``.
    After the package-backed migration, the real implementation lives in
    ``gamemodules.<name>.main`` and can stay cached across test-module imports,
    bypassing the import-time mocks those tests rely on.
    """

    try:
        source = Path(test_file).read_text(encoding="utf-8")
    except OSError:
        return

    for module_name in set(_GAMEMODULE_POP_RE.findall(source)):
        sys.modules.pop("gamemodules.%s.main" % (module_name,), None)


def pytest_pycollect_makemodule(module_path, parent):
    """Clear cached package submodules before pytest imports a test module."""

    _clear_cached_package_main_modules(module_path)
    return None


def _blocked(name):
    """Return a callable that raises RuntimeError when invoked."""
    def _fail(*args, **kwargs):
        raise RuntimeError(
            f"Network call blocked by tests/unit_tests/conftest.py: {name}() — "
            "add a mock in the test that needs it"
        )
    return _fail


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """Prevent real downloads in every unit test.

    * urllib — raises so tests that need it must supply their own mock.
    * steamcmd — silent no-op so _cov tests get coverage of install/update
      paths without triggering a real SteamCMD download.
    """
    monkeypatch.setattr(
        urllib.request, "urlopen", _blocked("urllib.request.urlopen")
    )
    monkeypatch.setattr(
        urllib.request, "urlretrieve", _blocked("urllib.request.urlretrieve")
    )
    try:
        import utils.steamcmd as _sc
        monkeypatch.setattr(_sc, "download", lambda *a, **kw: None)
        monkeypatch.setattr(_sc, "install_steamcmd", lambda *a, **kw: None)
        monkeypatch.setattr(
            _sc, "get_autoupdate_script",
            lambda name, path, app_id, force=False, mod=None: "/dev/null",
        )
    except ImportError:
        pass
