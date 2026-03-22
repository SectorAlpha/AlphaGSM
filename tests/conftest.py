import os
from unittest.mock import patch

os.environ['ALPHAGSM_CONFIG_LOCATION'] = './tests/alphagsm-test.conf'


def _blocked(name):
    """Return a callable that raises RuntimeError when invoked."""
    def _fail(*args, **kwargs):
        raise RuntimeError(
            f"Network call blocked by tests/conftest.py: {name}() — "
            "add a mock in the test that needs it"
        )
    return _fail


# Block real network access for every test in the suite.  Individual tests
# that need to verify download logic should mock the call themselves (via
# monkeypatch or unittest.mock); the per-test mock takes precedence.

_PATCHES = [
    patch("urllib.request.urlopen", new=_blocked("urllib.request.urlopen")),
    patch("urllib.request.urlretrieve", new=_blocked("urllib.request.urlretrieve")),
]

# steamcmd may not be importable in every environment (e.g. when only running
# _cov tests with sys.modules patching), so guard with try/except.
try:
    _PATCHES.append(
        patch("utils.steamcmd.download", new=_blocked("utils.steamcmd.download"))
    )
    _PATCHES.append(
        patch(
            "utils.steamcmd.install_steamcmd",
            new=_blocked("utils.steamcmd.install_steamcmd"),
        )
    )
except Exception:  # pragma: no cover
    pass


def pytest_runtest_setup(item):
    """Start all network-blocking patches before every test."""
    for p in _PATCHES:
        try:
            p.start()
        except Exception:  # pragma: no cover
            pass


def pytest_runtest_teardown(item, nextitem):
    """Stop all network-blocking patches after every test."""
    for p in _PATCHES:
        try:
            p.stop()
        except Exception:  # pragma: no cover
            pass