"""Placeholder module for a future Factorio server implementation.

This module intentionally raises `NotImplementedError` for now. Provide an
explicit `get_start_command` stub so static validators and callers receive a
clear error when attempting to start an unimplemented module.
"""

# download directory https://www.factorio.com/download-headless
def get_start_command(server):
	"""Not implemented for Factorio placeholder module."""
	raise NotImplementedError("Factorio game module is not implemented")

def get_runtime_requirements(server):
	"""Explicit runtime hook for placeholder modules.

	Raise `NotImplementedError` so callers and static checks get a clear
	failure instead of a silent miss.
	"""
	raise NotImplementedError("Factorio game module is not implemented")


def get_container_spec(server):
	"""Explicit container spec hook for placeholder modules."""
	raise NotImplementedError("Factorio game module is not implemented")

raise NotImplementedError("This game module has not been implemented yet")
