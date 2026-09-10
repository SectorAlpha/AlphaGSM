from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from utils.gamemodules.installers import download_steamcmd


def test_download_forwards_provider_and_branch_options():
    provider = SimpleNamespace(download=Mock())
    server = SimpleNamespace(data={"dir": "/srv/game"})
    options = {"beta": "preview"}
    download_steamcmd(
        server, steamcmd_module=provider, steam_app_id=123,
        steam_anonymous_login_possible=False, validate=True,
        download_kwargs=options,
    )
    provider.download.assert_called_once_with(
        "/srv/game", 123, False, validate=True, beta="preview"
    )
    assert options == {"beta": "preview"}


def test_download_propagates_provider_failure():
    error = RuntimeError("download failed")
    provider = SimpleNamespace(download=Mock(side_effect=error))
    with pytest.raises(RuntimeError) as caught:
        download_steamcmd(
            SimpleNamespace(data={"dir": "/srv/game"}),
            steamcmd_module=provider, steam_app_id=123,
            steam_anonymous_login_possible=True,
        )
    assert caught.value is error
