"""Preview and confirm deletion of module-declared world data."""

from pathlib import Path
import shutil
import tempfile

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


def _contained_path(root, relative):
    """Resolve one relative path and reject escapes and symlinks."""

    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ServerError("Unsafe wipe path: " + str(relative))
    target = root
    for part in relative.parts:
        target /= part
        if target.is_symlink():
            raise ServerError("Symlinked paths cannot be wiped: " + str(target))
    try:
        target.resolve().relative_to(root)
    except ValueError as exc:
        raise ServerError("Unsafe wipe path: " + str(relative)) from exc
    return target


def _install_root(server):
    """Return the server install directory after the hard-wipe safety checks."""

    root = Path(server.data["dir"]).resolve()
    if root == Path(root.anchor) or not root.is_dir() or root.is_symlink():
        raise ServerError("Unsafe install directory: " + str(root))
    return root


def _preserve_paths(server):
    """Return manager state plus module-declared configuration paths."""

    paths = [".alphagsm"]
    hook = getattr(server.module, "get_hard_wipe_preserve_paths", None)
    extra = hook(server) if callable(hook) else ()
    if extra:
        paths.extend(extra)
    seen = []
    for relative in paths:
        text = str(relative)
        if text not in seen:
            seen.append(text)
    return tuple(seen)


def _stage_preserved_paths(root, relatives, destination):
    """Copy existing preserved paths into *destination*."""

    copied = []
    for relative in relatives:
        target = _contained_path(root, relative)
        if not target.exists():
            continue
        staged = destination / relative
        staged.parent.mkdir(parents=True, exist_ok=True)
        if target.is_dir():
            shutil.copytree(target, staged, symlinks=False)
        else:
            shutil.copy2(target, staged)
        copied.append(relative)
    return tuple(copied)


def _restore_preserved_paths(staged_root, root, relatives):
    """Put staged configuration back after the install directory is rebuilt."""

    for relative in relatives:
        source = staged_root / relative
        if not source.exists():
            continue
        target = _contained_path(root, relative)
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target, symlinks=False)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def _clear_install_directory(root):
    """Remove install contents without following symlinks out of the directory."""

    for child in list(root.iterdir()):
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def hard_wipe(server, *, yes=False):
    """Reinstall server files and put declared configuration back afterwards."""

    _require_stopped(server)
    install = getattr(server.module, "install", None)
    if not callable(install):
        raise ServerError("Hard wipe is not supported for this server type.")
    root = _install_root(server)
    staged_root = Path(tempfile.mkdtemp(prefix="alphagsm-hard-wipe-"))
    try:
        copied = _stage_preserved_paths(root, _preserve_paths(server), staged_root)
        print("Hard wipe for %s reinstalls server files." % server.name)
        print("Configuration kept:")
        if copied:
            for relative in copied:
                print("  " + relative)
        else:
            print("  (none)")
        if not yes:
            try:
                confirmed = input("Reinstall this server and keep only that configuration? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                confirmed = ""
            if confirmed not in ("y", "yes"):
                print("Hard wipe cancelled.")
                return
        _require_stopped(server)
        _clear_install_directory(root)
        try:
            install(server)
        except Exception:
            _restore_preserved_paths(staged_root, root, copied)
            raise
        _restore_preserved_paths(staged_root, root, copied)
        print("Hard wipe complete.")
    finally:
        shutil.rmtree(staged_root, ignore_errors=True)
