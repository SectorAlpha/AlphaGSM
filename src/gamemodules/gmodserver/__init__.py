"""Package-backed canonical Garry's Mod module."""

from server.package_loader import load_package_surface


load_package_surface(globals())
del load_package_surface