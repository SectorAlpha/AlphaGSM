"""Grouped Arma 3 game modules.

This package defaults to the vanilla Arma 3 dedicated server module while also
exposing the existing Arma 3 variant modules under a namespaced layout.
"""

from .vanilla import *  # noqa: F401,F403

# Expose `get_start_command` directly for static inspection and callers that
# import this package module object.
try:
	from . import vanilla as _vanilla
	get_start_command = _vanilla.get_start_command
except Exception:
	# If vanilla cannot be imported at static-analysis time, fall back to a
	# placeholder that raises at runtime when invoked.
	def get_start_command(server):
		raise RuntimeError("Arma3 vanilla module unavailable")
