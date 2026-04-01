"""Verify the factorio module raises NotImplementedError on import."""

import pytest


def test_factorio_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        import gamemodules.factorio  # noqa: F401
