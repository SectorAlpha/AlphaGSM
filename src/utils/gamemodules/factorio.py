"""Placeholder module for a future Factorio server implementation (moved to utils).

This module intentionally raises `NotImplementedError` for now but lives under
`utils.gamemodules` so helper behavior is centralised.
"""

def get_start_command(server):
    raise NotImplementedError("Factorio game module is not implemented")


def get_runtime_requirements(server):
    raise NotImplementedError("Factorio game module is not implemented")


def get_container_spec(server):
    raise NotImplementedError("Factorio game module is not implemented")
