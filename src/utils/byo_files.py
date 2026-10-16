"""Game-owned BYO file contracts, acquisition guidance and read-only inspection."""

from copy import deepcopy
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import re
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


def load_requirements(server, module_file, manifest="byo_assets.json"):
    """Read a package-local recipe and resolve its declared instance path settings."""
    path = Path(module_file).with_name(manifest)
    try:
        recipe = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ServerError("Unable to read the module's BYO file requirements") from error
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
        if "any_of" in requirement:
            requirement["any_of"] = [_expand(value, values) for value in requirement["any_of"]]
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


def _archive_contains(path, member):
    """Inspect ZIP/PK3/IWD member names without extracting or loading game data."""
    try:
        with zipfile.ZipFile(path) as bundle:
            return any(info.file_size > 0 and not info.is_dir()
                       and fnmatch.fnmatchcase(info.filename, member)
                       for info in bundle.infolist())
    except (OSError, ValueError, zipfile.BadZipFile):
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
    if kind == "archive-member":
        relative_path(requirement.get("member", ""))
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
                    if kind != "archive-member" or _archive_contains(path, requirement["member"]):
                        return True
            except OSError:
                continue
    return False


def inspect_files(root, recipe):
    """Report declared file availability and source instructions, never readiness."""
    root = Path(root).absolute() if root else None
    missing, optional = [], []
    requirements = recipe.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        raise ServerError("This recipe does not declare BYO file requirements")
    for requirement in requirements:
        if not _satisfied(root, requirement, recipe.get("case_insensitive", False)):
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
