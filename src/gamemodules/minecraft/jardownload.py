"""Compatibility wrapper for shared Minecraft jar-download helpers.

Expose `get_start_command` only if the underlying helper provides one; this
keeps static checks happy while remaining a thin compatibility wrapper.
"""

from utils.gamemodules.minecraft.jardownload import *  # noqa: F401,F403

def get_start_command(server):
	"""Delegate to the underlying jardownload helper when present.

	This wrapper is not a server module; calling this will usually raise
	`NotImplementedError` from the underlying helper.
	"""
	try:
		from utils.gamemodules.minecraft import jardownload as _impl

		return _impl.get_start_command(server)
	except Exception:
		raise NotImplementedError("jardownload helper does not implement get_start_command")
