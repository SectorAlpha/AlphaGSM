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
	# Delegate runtime hooks to the vanilla module so the package-level
	# `arma3` surface exposes the full runtime contract for static inspection.
	get_runtime_requirements = _vanilla.get_runtime_requirements
	get_container_spec = _vanilla.get_container_spec
except Exception:
	# If vanilla cannot be imported at static-analysis time, fall back to a
	# placeholder that raises at runtime when invoked.
	def get_start_command(server):
		raise RuntimeError("Arma3 vanilla module unavailable")

	def get_runtime_requirements(server):
		raise RuntimeError("Arma3 vanilla runtime hooks unavailable")

	def get_container_spec(server):
		raise RuntimeError("Arma3 vanilla container spec unavailable")
