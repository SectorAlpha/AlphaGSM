"""Game-owned BYO file contracts, acquisition guidance and read-only inspection."""

from copy import deepcopy
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

from server.errors import ServerError


def relative_path(value):
    """Validate a portable relative path or glob without touching the filesystem."""
    value = str(value)
    if (not value or value.startswith("/") or any(char in value for char in "\\:\x00\r\n")
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ServerError("Unsafe BYO requirement path: " + value)
    return value


def _expand(value, values):
    """Expand only named, non-secret module settings in recipe path fields."""
    def substitute(match):
        key = match.group(1)
        if key not in values:
            raise ServerError("Unknown BYO path setting: " + key)
        return str(values[key])
    result = re.sub(r"\{([A-Za-z_]+)\}", substitute, str(value))
    if "{" in result or "}" in result:
        raise ServerError("Invalid BYO path template")
    return relative_path(result)


def _prepare_external_home(server, recipe):
    """Inspect opted-in absolute config homes without permitting managed writes."""
    if "config_home_setting" not in recipe:
        return
    setting = recipe["config_home_setting"]
    if setting not in ("configdir", "confdir"):
        raise ServerError("Invalid BYO configuration home setting: " + str(setting))
    home = server.data.get(setting, recipe.get("defaults", {}).get(setting, ""))
    if not os.path.isabs(str(home)):
        return
    prefix = "{" + setting + "}/"
    for requirement in recipe["requirements"]:
        for key in ("path", "any_of"):
            if key not in requirement:
                continue
            values = [requirement[key]] if key == "path" else requirement[key]
            translated = []
            for value in values:
                if not value.startswith(prefix):
                    raise ServerError("BYO requirement path is outside the configuration home")
                translated.append(relative_path(value[len(prefix):]))
            requirement[key] = translated[0] if key == "path" else translated
    recipe.update(root_setting=setting, target="", managed_import=False,
                  manual_reason="An absolute configuration home requires manual staging. "
                  "Copy server_packages.sii and server_packages.dat into the configured home, "
                  "then run assets check.")


def load_requirements(server, module_file, manifest="byo_assets.json"):
    """Read a package-local recipe and resolve its declared instance path settings."""
    path = Path(module_file).with_name(manifest)
    try:
        recipe = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ServerError("Unable to read the module's BYO file requirements") from error
    _prepare_external_home(server, recipe)
    values = {"server_name": server.name}
    allowed = {"exe_name", "configdir", "confdir", "cluster", "shard", "startmap", "map"}
    for key, default in recipe.get("defaults", {}).items():
        if key not in allowed:
            raise ServerError("Invalid BYO path setting: " + key)
        values[key] = server.data.get(key, str(default).replace("{server_name}", server.name))
    for requirement in recipe["requirements"]:
        for key in ("path", "member"):
            if key in requirement:
                requirement[key] = _expand(requirement[key], values)
        for key in ("any_of", "member_any_of"):
            if key in requirement:
                alternatives = _member_patterns(requirement) if key == "member_any_of" else requirement[key]
                requirement[key] = [_expand(value, values) for value in alternatives]
    for key in ("required", "include", "roots"):
        if key in recipe:
            recipe[key] = [_expand(value, values) if value else "" for value in recipe[key]]
    if "required_any" in recipe:
        recipe["required_any"] = [[_expand(value, values) for value in group] for group in recipe["required_any"]]
    if recipe.get("target"):
        recipe["target"] = _expand(recipe["target"], values)
    return recipe


def inspection_root(server, recipe):
    """Resolve the declared install root or explicit external owned-game location."""
    if recipe.get("root_setting") or recipe.get("root_env"):
        return (server.data.get(recipe.get("root_setting", ""))
                or os.environ.get(recipe.get("root_env", "")))
    return server.data.get("dir")


def _unlinked(root, candidate):
    """Keep inspection inside its root and never accept symlinked content."""
    try:
        candidate.relative_to(root)
        for path in (candidate, *candidate.parents):
            if path.is_symlink():
                return False
            if path == root:
                return True
    except (ValueError, OSError):
        return False
    return False


def _matches(root, pattern, insensitive=False):
    """Yield matching paths without following symbolic directory links."""
    if insensitive:
        for candidate in root.rglob("*"):
            if PurePosixPath("/" + candidate.relative_to(root).as_posix().casefold()).match("/" + pattern.casefold()):
                yield candidate
    else:
        yield from root.glob(pattern)


def _member_patterns(requirement):
    """Validate archive member alternatives, retaining the single-member contract."""
    members = requirement.get("member_any_of", [requirement.get("member", "")])
    if not isinstance(members, list) or not members:
        raise ServerError("BYO archive member alternatives must be nonempty lists")
    return [relative_path(member) for member in members]


def _archive_contains(path, members, insensitive=False):
    """Inspect regular ZIP/PK3/IWD members without extracting or loading data."""
    patterns = [member.casefold() if insensitive else member for member in members]
    try:
        with zipfile.ZipFile(path) as bundle:
            for info in bundle.infolist():
                if (info.file_size <= 0 or info.is_dir()
                        or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG)):
                    continue
                name = info.filename.replace("\\", "/")
                while name.startswith("./"):
                    name = name[2:]
                if insensitive:
                    name = name.casefold()
                if any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):
                    return True
    except (OSError, ValueError, zipfile.BadZipFile):
        return False
    return False


def _satisfied(root, requirement, insensitive):
    """Check one declared file, alternative group, populated directory or archive."""
    kind = requirement.get("kind", "file")
    if kind not in {"file", "glob", "directory", "archive-member"}:
        raise ServerError("Unsupported BYO file requirement kind: " + str(kind))
    patterns = requirement.get("any_of", [requirement.get("path", "")])
    if not patterns:
        raise ServerError("BYO file alternatives cannot be empty")
    for pattern in patterns:
        relative_path(pattern)
    members = _member_patterns(requirement) if kind == "archive-member" else []
    if root is None:
        return False
    for pattern in patterns:
        for path in _matches(root, pattern, insensitive):
            try:
                if not _unlinked(root, path):
                    continue
                if kind == "directory":
                    if path.is_dir() and any(_unlinked(root, entry) and entry.is_file()
                                            and entry.stat().st_size > 0 for entry in path.rglob("*")):
                        return True
                elif path.is_file() and (not requirement.get("nonempty", True) or path.stat().st_size > 0):
                    if kind != "archive-member" or _archive_contains(
                            path, members, requirement.get("member_case_insensitive", False)):
                        return True
            except OSError:
                continue
    return False


def inspect_files(root, recipe, *, source=False):
    """Inspect installed paths natively; source paths may use recipe case folding."""
    root = Path(root).absolute() if root else None
    missing, optional = [], []
    requirements = recipe.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        raise ServerError("This recipe does not declare BYO file requirements")
    insensitive = recipe.get("case_insensitive", False) if source else False
    for requirement in requirements:
        if not _satisfied(root, requirement, insensitive):
            label = requirement.get("path") or " or ".join(requirement["any_of"])
            (optional if requirement.get("optional") else missing).append(label)
    return {"status": "missing" if missing else "ready", "ready": not missing,
            "missing": missing, "optional_missing": optional,
            "requirements": deepcopy(requirements), "sources": deepcopy(recipe.get("sources", [])),
            "validation": recipe.get("validation", "declared-files"),
            "managed_import": recipe.get("managed_import", False),
            "game_readiness": "not-checked"}


def require_managed_import(recipe):
    """Fail explicitly when a game needs manual staging or richer validation."""
    if recipe.get("managed_import", True) is False:
        raise ServerError(recipe.get("manual_reason", "This payload requires manual staging; inspect assets requirements"))


def validate_staged_files(staging, recipe, target):
    """Check only selected bytes against game requirements before publishing."""
    declaration = deepcopy(recipe)
    for item in declaration['requirements']:
        keys = ('path',) if 'path' in item else ('any_of',)
        for key in keys:
            values = [item[key]] if key == 'path' else item[key]
            translated = []
            for value in values:
                if target:
                    if not value.startswith(target + '/'):
                        raise ServerError('A required file is outside this import target')
                    value = value[len(target) + 1:]
                translated.append(value)
            item[key] = translated[0] if key == 'path' else translated
    report = inspect_files(staging, declaration)
    if not report['ready']:
        raise ServerError('Selected content lacks required files: ' + ', '.join(report['missing']))


_ARCHIVE_SUFFIXES = {".pk3", ".iwd", ".zip"}
_MP_MEMBER = re.compile(r"^maps/(?:mp/)?(mp_[^/]+)\.(?:bsp|d3dbsp)$", re.IGNORECASE)
_Q3_MEMBER = re.compile(
    r"^maps/(q3tourney6_ctf|q3dm\d+|q3tourney\d+|q3ctf\d+|pro-q3[a-z0-9]+|test_bigbox)\.bsp$",
    re.IGNORECASE,
)


def _dedicated_map_name(filename):
    """Return a dedicated multiplayer map stem, ignoring campaign and load screens."""

    stem, extension = os.path.splitext(filename)
    lowered = stem.casefold()
    if extension.casefold() not in {".ff", ".bsp", ".d3dbsp"}:
        return None
    if lowered.startswith("sp_") or lowered.endswith("_load"):
        return None
    if lowered.startswith("mp_"):
        return lowered
    if _Q3_MEMBER.fullmatch("maps/" + stem + ".bsp"):
        return lowered
    return None


def _maps_in_archive(path):
    """Read multiplayer map names from a PK3, IWD or zip without extracting it."""

    names = set()
    try:
        with zipfile.ZipFile(path) as bundle:
            for info in bundle.infolist():
                if info.file_size <= 0 or info.is_dir():
                    continue
                member = info.filename.replace("\\", "/")
                while member.startswith("./"):
                    member = member[2:]
                match = _MP_MEMBER.fullmatch(member) or _Q3_MEMBER.fullmatch(member)
                if match and not match.group(1).casefold().endswith("_load"):
                    names.add(match.group(1).casefold())
    except (OSError, ValueError, zipfile.BadZipFile):
        return set()
    return names


def multiplayer_map_names(root):
    """List dedicated multiplayer maps found as loose files or inside archives."""

    names = set()
    root = os.fspath(root)
    if not os.path.isdir(root):
        return []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames
            if not os.path.islink(os.path.join(dirpath, name))
        ]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if os.path.splitext(filename)[1].casefold() in _ARCHIVE_SUFFIXES:
                names.update(_maps_in_archive(path))
                continue
            discovered = _dedicated_map_name(filename)
            if discovered:
                names.add(discovered)
    return sorted(names)


def missing_multiplayer_maps(root, required):
    """Return required dedicated maps that are absent from a server build."""

    found = set(multiplayer_map_names(root))
    return [str(name) for name in required if str(name).casefold() not in found]


def require_module_multiplayer_maps(install_dir, module_file):
    """Apply the module recipe's dedicated multiplayer map list to one build."""

    server = type("MapCheck", (), {"name": "map-check", "data": {}})()
    recipe = load_requirements(server, module_file)
    require_multiplayer_maps(install_dir, recipe.get("multiplayer_maps") or [])


def require_multiplayer_maps(root, required):
    """Fail when a build that already has dedicated maps is missing one of them.

    An engine archive with no map bytes is not a map build. Callers still
    reject that tree with their own base-asset check.
    """

    if not multiplayer_map_names(root):
        return
    missing = missing_multiplayer_maps(root, required)
    if missing:
        raise ServerError("Dedicated server is missing multiplayer maps: " + ", ".join(missing))


def assert_multiplayer_maps_retained(source, published):
    """Fail when publication drops a multiplayer map that the source contained."""

    discovered = multiplayer_map_names(source)
    if not discovered:
        return
    missing = missing_multiplayer_maps(published, discovered)
    if missing:
        raise ServerError(
            "Published dedicated server is missing multiplayer maps: " + ", ".join(missing)
        )
