"""Helpers for package-backed game module import surfaces."""

from __future__ import annotations

from pathlib import Path
import sys


def load_package_surface(package_globals):
    """Execute ``main.py`` into the package module namespace.

    This keeps the canonical import surface at ``gamemodules.<name>`` while
    avoiding a cached ``gamemodules.<name>.main`` submodule becoming shared
    mutable state across test-module imports.
    """

    package_name = package_globals["__name__"]
    main_path = Path(package_globals["__file__"]).with_name("main.py")
    source = main_path.read_text(encoding="utf-8")
    exec(compile(source, str(main_path), "exec"), package_globals)  # pylint: disable=exec-used
    package_module = sys.modules[package_name]
    package_globals["_main"] = package_module
    sys.modules[package_name + ".main"] = package_module