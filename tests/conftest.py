import os
import urllib.request

import pytest

os.environ['ALPHAGSM_CONFIG_LOCATION'] = './tests/alphagsm-test.conf'


def _blocked(name):
    """Return a callable that raises RuntimeError when invoked."""
    def _fail(*args, **kwargs):
        raise RuntimeError(
            f"Network call blocked by tests/conftest.py: {name}() — "
            "add a mock in the test that needs it"
        )
    return _fail


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """Prevent real downloads in every test.

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