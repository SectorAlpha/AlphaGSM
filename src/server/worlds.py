"""Preview and confirm deletion of module-declared world data."""

from pathlib import Path
import shutil

from .errors import ServerError
from . import runtime as runtime_module


def _wipe_plan(server):
    hook = getattr(server.module, "get_wipe_paths", None)
    paths = hook(server) if callable(hook) else getattr(server.module, "wipe_paths", None)
    if paths is None:
        raise ServerError("Wipe is not supported for this server type.")
    root_hook = getattr(server.module, "get_wipe_root", None)
    root = Path(root_hook(server) if callable(root_hook) else server.data["dir"]).resolve()
    if root == Path(root.anchor):
        raise ServerError("Unsafe world data root: " + str(root))
    plan = {}
    for relative in paths:
        relative = Path(relative)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ServerError("Unsafe world path: " + str(relative))
        target = root
        for part in relative.parts:
            target /= part
            if target.is_symlink():
                raise ServerError("Symlinked world paths cannot be wiped: " + str(target))
        if not target.exists():
            continue
        stat = target.stat()
        plan[target] = (stat.st_dev, stat.st_ino, stat.st_mode, stat.st_mtime_ns)
    # An entire directory already includes its descendants.
    return tuple((path, identity) for path, identity in sorted(plan.items())
                 if not any(parent in plan for parent in path.parents))


def _require_stopped(server):
    if runtime_module.check_server_running(server):
        raise ServerError("Error: Cannot wipe a running server. Stop it first.")


def wipe_worlds(server, *, yes=False):
    """Delete only the validated targets shown in the confirmation preview."""

    _require_stopped(server)
    plan = _wipe_plan(server)
    if not plan:
        print("No world files found; nothing to delete.")
        return
    print("World data to delete for %s:" % server.name)
    for target, _ in plan:
        kind = "directory and all contents" if target.is_dir() else "file"
        print("  %s (%s)" % (target, kind))
    if not yes:
        try:
            confirmed = input("Permanently delete this world data? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirmed = ""
        if confirmed not in ("y", "yes"):
            print("World reset cancelled.")
            return
    _require_stopped(server)
    if _wipe_plan(server) != plan:
        raise ServerError("World paths changed after the preview; run wipe again.")
    for target, _ in plan:
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        except OSError as exc:
            raise ServerError("Failed to remove: " + str(target)) from exc
        print("Removed: " + str(target))
