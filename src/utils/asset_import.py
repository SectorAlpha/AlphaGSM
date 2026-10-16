"""Import operator-owned game assets using portable, explicit file recipes.

Recipes contain ``roots``, ``include``, ``required`` and ``target`` paths using
forward slashes. Imports never extract an archive wholesale or remove files.
Only unchanged files recorded in the ownership manifest may be replaced.
"""

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile
import zipfile

from server import ServerError


_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.IGNORECASE)
_MANIFEST = ".alphagsm/assets.json"


@dataclass
class _Asset:
    """One validated, readable source file."""

    size: int
    opener: object


@dataclass
class _Selection:
    """Allowlisted files underneath one unambiguous recipe root."""

    source: Path
    root: str
    files: dict
    target: str


def _portable_name(name, *, directory=False):
    """Validate names on every host, including Windows filesystem constraints."""
    if directory:
        name = name.rstrip("/")
    while name.startswith("./"):
        name = name[2:]
    if directory and name in ("", "."):
        return ""
    parts = name.split("/")
    if any(
        part in ("", ".", "..")
        or part.endswith((" ", "."))
        or _RESERVED.match(part)
        or any(ord(char) < 32 or char in '<>:"\\|?*' for char in part)
        for part in parts
    ):
        raise ServerError("Unsafe or non-portable asset path: %s" % name)
    return "/".join(parts)


def _assert_no_links(path):
    """Reject symlinks and Windows reparse points in an existing path."""
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ServerError("Links are not permitted in asset paths: %s" % candidate)
        if candidate.exists():
            attributes = getattr(candidate.lstat(), "st_file_attributes", 0)
            if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ServerError("Links are not permitted in asset paths: %s" % candidate)


def _assert_case_matches(path):
    """Keep destination spelling consistent on case-sensitive and Windows hosts."""
    for candidate in (path, *path.parents):
        if candidate.parent.is_dir():
            if any(name.casefold() == candidate.name.casefold() and name != candidate.name
                   for name in os.listdir(candidate.parent)):
                raise ServerError("Portable case collision in asset destination: %s" % candidate)


def _register_name(names, name, *, directory=False):
    """Detect duplicate files, filename case collisions and file/directory clashes."""
    pieces = name.split("/")
    for index in range(1, len(pieces) + 1):
        prefix = "/".join(pieces[:index])
        kind = "directory" if directory or index < len(pieces) else "file"
        previous = names.get(prefix.casefold())
        if previous and previous != (prefix, kind):
            raise ServerError("Portable case collision or file/directory conflict: %s" % name)
        if previous and kind == "file":
            raise ServerError("Duplicate asset file: %s" % name)
        names[prefix.casefold()] = (prefix, kind)


def _directory_entries(source):
    """Inventory a directory without following links or special files."""
    entries, names = {}, {}
    for root, directories, files in os.walk(source, followlinks=False):
        for filename in directories + files:
            path = Path(root) / filename
            _assert_no_links(path)
            mode = path.stat().st_mode
            is_directory = stat.S_ISDIR(mode)
            name = _portable_name(path.relative_to(source).as_posix(), directory=is_directory)
            _register_name(names, name, directory=is_directory)
            if not is_directory:
                if not stat.S_ISREG(mode):
                    raise ServerError("Asset must be a regular file: %s" % path)
                entries[name] = _Asset(path.stat().st_size, lambda file=path: file.open("rb"))
    return entries


def _zip_entries(bundle):
    """Inventory ZIP records without trusting archive paths or Unix attributes."""
    entries, names = {}, {}
    for member in bundle.infolist():
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ServerError("Links are not permitted in asset archives: %s" % member.filename)
        is_directory = member.is_dir()
        if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ServerError("Unsafe nonregular archive member: %s" % member.filename)
        name = _portable_name(member.filename, directory=is_directory)
        if name:
            _register_name(names, name, directory=is_directory)
            if not is_directory:
                entries[name] = _Asset(member.file_size, lambda item=member: bundle.open(item))
    return entries


def _tar_entries(bundle):
    """Inventory tar files while forbidding all links and special members."""
    entries, names = {}, {}
    for member in bundle.getmembers():
        if member.issym() or member.islnk():
            raise ServerError("Links are not permitted in asset archives: %s" % member.name)
        if not member.isfile() and not member.isdir():
            raise ServerError("Unsafe nonregular archive member: %s" % member.name)
        name = _portable_name(member.name, directory=member.isdir())
        if name:
            _register_name(names, name, directory=member.isdir())
            if member.isfile():
                entries[name] = _Asset(member.size, lambda item=member: bundle.extractfile(item))
    return entries


@contextmanager
def _open_source(source):
    """Keep archive handles alive until all selected files have been staged."""
    source = Path(source).absolute()
    _assert_no_links(source)
    source = source.resolve()
    with ExitStack() as stack:
        if source.is_dir():
            entries = _directory_entries(source)
        elif not source.is_file():
            raise ServerError("Asset source does not exist: %s" % source)
        elif zipfile.is_zipfile(source):
            entries = _zip_entries(stack.enter_context(zipfile.ZipFile(source)))
        elif tarfile.is_tarfile(source):
            entries = _tar_entries(stack.enter_context(tarfile.open(source, "r:*")))
        else:
            raise ServerError("Asset source must be a directory, ZIP or tar archive: %s" % source)
        yield source, entries


def _recipe_paths(recipe):
    """Validate recipe paths before using them to construct destinations."""
    required = tuple(_portable_name(str(name)) for name in recipe.get("required", ()))
    if not required:
        raise ServerError("Asset recipe must declare required files")
    target = str(recipe.get("target", ""))
    target = _portable_name(target) if target else ""
    roots = tuple(_portable_name(str(root)) if root else "" for root in recipe.get("roots", ("",)))
    patterns = tuple(str(pattern) for pattern in recipe.get("include", ()))
    for pattern in patterns:
        _portable_name(pattern.replace("*", "x").replace("?", "x"))
    if not patterns:
        raise ServerError("Asset recipe must declare included files")
    return required, target, roots, patterns


def _join(root, path):
    """Join canonical archive-style paths without host-dependent separators."""
    return root + "/" + path if root else path


def _candidate_roots(entries, roots):
    """Consider declared roots and one enclosing archive/export directory."""
    candidates = set(roots)
    top_directories = {name.split("/")[0] for name in entries if "/" in name}
    for dirname in top_directories:
        candidates.update(_join(dirname, root) for root in roots)
    return sorted(candidates)


def _select(source, entries, recipe):
    """Select an unambiguous complete root before creating destination files."""
    required, target, roots, patterns = _recipe_paths(recipe)
    insensitive = recipe.get("case_insensitive", False)
    canonical = {name.lower() if insensitive else name: (name, asset)
                 for name, asset in entries.items()}
    required = tuple(name.lower() if insensitive else name for name in required)
    patterns = tuple(name.lower() if insensitive else name for name in patterns)
    roots = tuple(name.lower() if insensitive else name for name in roots)
    candidates = _candidate_roots(canonical, roots)
    matches = [root for root in candidates if all(
        _join(root, name) in canonical and canonical[_join(root, name)][1].size > 0
        for name in required)]
    if len(matches) > 1:
        raise ServerError("Ambiguous asset roots: %s" % ", ".join(root or "." for root in matches))
    if not matches:
        raise ServerError("Missing or empty required assets: %s" % ", ".join(required))
    root = matches[0]
    files = {}
    for name, (_, asset) in canonical.items():
        if root and not name.startswith(root + "/"):
            continue
        relative = name[len(root) + 1:] if root else name
        if any(PurePosixPath("/" + relative).match("/" + pattern) for pattern in patterns):
            files[relative] = asset
    if any(name not in files for name in required):
        raise ServerError("Required assets must also match the recipe include patterns")
    return _Selection(source, root, dict(sorted(files.items())), target)


def _hash_file(path):
    """Hash large map files with bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(install_root):
    """Load only manifests written with the supported ownership schema."""
    path = install_root / _MANIFEST
    _assert_no_links(path)
    _assert_case_matches(path)
    if not path.exists():
        return {"version": 1, "files": {}}
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ServerError("Unsupported asset ownership manifest: %s" % path)
    records = manifest.get("files")
    if not isinstance(records, dict) or any(
        not isinstance(record, dict) or not isinstance(record.get("sha256"), str)
        for record in records.values()
    ):
        raise ServerError("Invalid asset ownership manifest: %s" % path)
    return manifest


def _stage_selection(selection, staging):
    """Read and hash each allowed file before publication begins."""
    records = {}
    for name, asset in selection.files.items():
        staged = staging / "new" / name
        staged.parent.mkdir(parents=True, exist_ok=True)
        with asset.opener() as source, staged.open("wb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        if staged.stat().st_size != asset.size:
            raise ServerError("Asset changed while being read: %s" % name)
        records[_join(selection.target, name)] = {
            "sha256": _hash_file(staged), "size": asset.size,
        }
    return records


def _publication_plan(install_root, records, manifest):
    """Validate ownership and all destination paths before modifying any file."""
    copied, skipped = [], []
    for name, record in records.items():
        if name.split("/")[0].casefold() == ".alphagsm":
            raise ServerError("Asset recipe cannot replace reserved AlphaGSM metadata")
        destination = install_root / name
        _assert_no_links(destination)
        _assert_case_matches(destination)
        for parent in destination.parents:
            if parent.exists() and not parent.is_dir():
                raise ServerError("Asset destination parent is not a directory: %s" % parent)
        previous = manifest["files"].get(name)
        if destination.exists():
            if not destination.is_file():
                raise ServerError("Asset destination is not a regular file: %s" % destination)
            current_hash = _hash_file(destination)
            if previous is None:
                if current_hash == record["sha256"]:
                    skipped.append(name)
                    continue
                raise ServerError("Refusing to replace unrelated, unowned asset: %s" % name)
            if current_hash != previous["sha256"]:
                raise ServerError("Refusing to replace externally modified asset: %s" % name)
            if current_hash == record["sha256"]:
                skipped.append(name)
                continue
        copied.append(name)
    return copied, skipped


def _mkdir_tracked(path, created):
    """Remember new directories so rollback leaves no empty installation tree."""
    missing = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    for directory in reversed(missing):
        directory.mkdir()
        created.append(directory)


def _publish(install_root, selection, staging, copied, manifest):
    """Publish staged files and manifest, restoring previous bytes on any failure."""
    published, created = [], []
    operations = [(name, staging / "new" / name[len(selection.target) + 1:]
                   if selection.target else staging / "new" / name) for name in copied]
    staged_manifest = staging / "manifest.json"
    staged_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    operations.append((_MANIFEST, staged_manifest))
    try:
        for index, (name, staged) in enumerate(operations):
            destination = install_root / name
            backup = staging / ("backup-%s" % index)
            _mkdir_tracked(destination.parent, created)
            existed = destination.exists()
            if existed:
                shutil.copy2(destination, backup)
            os.replace(staged, destination)
            published.append((destination, backup if existed else None))
    except OSError:
        for destination, backup in reversed(published):
            if backup is None:
                destination.unlink()
            else:
                os.replace(backup, destination)
        for directory in reversed(created):
            directory.rmdir()
        raise


def import_assets(source, install_root, recipe):
    """Validate and transactionally import allowlisted assets, preserving ownership."""
    try:
        with _open_source(source) as (source_path, entries):
            selection = _select(source_path, entries, recipe)
            install_root = Path(install_root).absolute()
            _assert_no_links(install_root)
            install_root = install_root.resolve()
            manifest = _load_manifest(install_root)
            # The nearest existing ancestor guarantees staging stays on this filesystem.
            staging_parent = install_root
            while not staging_parent.exists():
                staging_parent = staging_parent.parent
            with tempfile.TemporaryDirectory(prefix=".alphagsm-assets-", dir=staging_parent) as temp:
                staging = Path(temp)
                records = _stage_selection(selection, staging)
                copied, skipped = _publication_plan(install_root, records, manifest)
                manifest["files"].update({name: records[name] for name in copied})
                _publish(install_root, selection, staging, copied, manifest)
        return {"status": "ready", "files": list(records), "copied": copied,
                "skipped": skipped, "manifest": str(install_root / _MANIFEST)}
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile, RuntimeError) as error:
        raise ServerError("Unable to import assets: %s" % error) from error


def check_assets(install_root, recipe):
    """Report missing or empty required installed files without creating anything."""
    required, target, _, _ = _recipe_paths(recipe)
    if recipe.get("case_insensitive", False):
        required = tuple(name.lower() for name in required)
    install_root = Path(install_root).absolute()
    files, missing = [], []
    try:
        for name in required:
            relative = _join(target, name)
            path = install_root / relative
            _assert_no_links(path)
            if path.is_file() and path.stat().st_size > 0:
                files.append(relative)
            else:
                missing.append(relative)
    except OSError as error:
        raise ServerError("Unable to check assets: %s" % error) from error
    return {"status": "missing" if missing else "ready", "ready": not missing,
            "missing": missing, "files": files}


def export_assets(source, output, recipe):
    """Package validated allowed files in a portable ZIP, replacing output atomically."""
    try:
        with _open_source(source) as (source_path, entries):
            selection = _select(source_path, entries, recipe)
            output = Path(output).absolute()
            _assert_no_links(output)
            output = output.resolve()
            if output == source_path or (source_path.is_dir() and source_path in output.parents):
                raise ServerError("Export output must be outside the asset source directory")
            with tempfile.TemporaryDirectory(prefix=".alphagsm-export-", dir=output.parent) as temp:
                staged = Path(temp) / "assets.zip"
                with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                    for name, asset in selection.files.items():
                        with asset.opener() as incoming, bundle.open(name, "w", force_zip64=True) as outgoing:
                            shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
                with zipfile.ZipFile(staged) as bundle:
                    if any(bundle.getinfo(name).file_size != asset.size
                           for name, asset in selection.files.items()):
                        raise ServerError("Asset changed while being exported")
                os.replace(staged, output)
        return {"status": "ready", "output": str(output), "files": list(selection.files)}
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile, RuntimeError) as error:
        raise ServerError("Unable to export assets: %s" % error) from error
