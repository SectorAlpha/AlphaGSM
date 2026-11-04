"""Read an explicitly selected Steam library's public installation metadata.

Only known library-list files and the requested app manifest are inspected.
This resolver never accesses account caches, scans game files, or changes Steam
state. The asset importer remains responsible for validating selected files.
"""

import os
from pathlib import Path
import re
import stat

from server import ServerError


_METADATA_LIMIT = 1024 * 1024
_MAX_DEPTH = 16
_RESERVED_NAME = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.IGNORECASE)


class _KeyValues:
    """Parse the bounded quoted-string/object subset used by public Steam files."""

    def __init__(self, source):
        self.source = source
        self.position = 0

    def _token(self):
        """Return a (kind, value) token; no unquoted strings or directives."""
        while self.position < len(self.source):
            char = self.source[self.position]
            if char.isspace():
                self.position += 1
            elif self.source.startswith("//", self.position):
                newline = self.source.find("\n", self.position)
                self.position = len(self.source) if newline == -1 else newline + 1
            else:
                break
        if self.position == len(self.source):
            return "end", ""
        char = self.source[self.position]
        self.position += 1
        if char in "{}":
            return char, char
        if char != '"':
            raise ValueError("Unsupported token")
        value = []
        while self.position < len(self.source):
            char = self.source[self.position]
            self.position += 1
            if char == '"':
                return "string", "".join(value)
            if char == "\x00":
                raise ValueError("NUL in string")
            if char == "\\":
                if self.position == len(self.source) or self.source[self.position] not in ('"', "\\"):
                    raise ValueError("Unsupported escape")
                char = self.source[self.position]
                self.position += 1
            value.append(char)
        raise ValueError("Unclosed string")

    def mapping(self, depth=0):
        """Read a complete object, rejecting duplicate case-insensitive keys."""
        if depth > _MAX_DEPTH:
            raise ValueError("Excessive nesting")
        result = {}
        while True:
            kind, key = self._token()
            if kind == "end" and depth == 0 or kind == "}" and depth > 0:
                return result
            if kind != "string" or key.casefold() in result:
                raise ValueError("Invalid or duplicate key")
            kind, value = self._token()
            if kind == "{":
                value = self.mapping(depth + 1)
            elif kind != "string":
                raise ValueError("Missing value")
            result[key.casefold()] = value


def _regular_metadata(info):
    """Reject links, Windows reparse points and nonregular metadata."""
    attributes = getattr(info, "st_file_attributes", 0)
    if not stat.S_ISREG(info.st_mode) or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
        raise ServerError("Steam metadata must be a regular file without links")
    if info.st_size > _METADATA_LIMIT:
        raise ServerError("Steam metadata exceeds 1 MiB")


def _read_metadata(path):
    """Read at most 1 MiB plus a sentinel byte, without following file links."""
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        raise ServerError("Cannot safely read Steam metadata") from None
    _regular_metadata(before)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as source:
            opened = os.fstat(source.fileno())
            _regular_metadata(opened)
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise ServerError("Steam metadata changed while being opened")
            raw = source.read(_METADATA_LIMIT + 1)
    except OSError:
        raise ServerError("Cannot safely read Steam metadata") from None
    if len(raw) > _METADATA_LIMIT:
        raise ServerError("Steam metadata exceeds 1 MiB")
    try:
        return _KeyValues(raw.decode("utf-8-sig")).mapping()
    except (UnicodeError, ValueError):
        raise ServerError("Invalid or unsupported Steam KeyValues metadata") from None


def _app_id(value):
    """Normalize only ASCII decimal IDs in Steam's unsigned 32-bit range."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ServerError("Invalid Steam app ID; use a decimal integer from 1 to 4294967295")
    value = str(value)
    # Strip zeroes before the length check, avoiding Python's huge-integer limit.
    canonical = value.lstrip("0")
    if (re.fullmatch(r"[0-9]+", value) is None or not canonical or len(canonical) > 10
            or int(canonical) > 4294967295):
        raise ServerError("Invalid Steam app ID; use a decimal integer from 1 to 4294967295")
    return canonical


def _listed_libraries(root):
    """Read only the two known public library-list locations."""
    for path in (root / "steamapps/libraryfolders.vdf", root / "config/libraryfolders.vdf"):
        metadata = _read_metadata(path)
        if metadata is None:
            continue
        entries = metadata.get("libraryfolders")
        if not isinstance(entries, dict):
            raise ServerError("Invalid Steam library-list metadata")
        for key, value in entries.items():
            if re.fullmatch(r"[0-9]+", key) is None:
                continue
            value = value.get("path") if isinstance(value, dict) else value
            if not isinstance(value, str) or not value or "\x00" in value:
                raise ServerError("Invalid Steam library path metadata")
            path = Path(value)
            if not path.is_absolute():
                raise ServerError("Steam library path metadata must be absolute")
            yield path / "steamapps"


def _library_directories(steam_dir):
    """Resolve only the supplied root and its explicitly listed libraries."""
    try:
        requested = Path(steam_dir).expanduser()
        explicit = requested.name.casefold() == "steamapps"
        root = requested.resolve(strict=True)
        primary = root if explicit else root / "steamapps"
        if not root.is_dir() or not primary.is_dir():
            raise ServerError("Steam directory must contain steamapps or be a steamapps directory")
        candidates = [primary]
        if not explicit:
            candidates.extend(_listed_libraries(root))
        seen = set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve(strict=True)
                available = resolved.is_dir()
            except (OSError, RuntimeError):
                continue
            if available and resolved not in seen:
                seen.add(resolved)
                yield resolved
    except (OSError, RuntimeError, TypeError, ValueError):
        raise ServerError("Steam directory is unavailable or invalid") from None


def _installed_directory(apps, app_id):
    """Require the matching AppState and a portable contained game directory."""
    metadata = _read_metadata(apps / ("appmanifest_" + app_id + ".acf"))
    if metadata is None:
        return None
    state = metadata.get("appstate")
    if not isinstance(state, dict) or state.get("appid") != app_id:
        raise ServerError("Steam app manifest AppState ID does not match the requested app")
    name = state.get("installdir")
    if not isinstance(name, str):
        raise ServerError("Steam app manifest installdir must be a directory name")
    if (name in ("", ".", "..") or name.endswith((" ", ".")) or _RESERVED_NAME.match(name)
            or any(ord(char) < 32 or ord(char) == 127 or char in '/\\<>:"|?*' for char in name)):
        raise ServerError("Steam app installdir must be one portable directory name")
    try:
        common = (apps / "common").resolve(strict=True)
        game = (common / name).resolve(strict=True)
        if not game.is_relative_to(common):
            raise ServerError("Steam app installation escapes the library common directory")
        return game if game.is_dir() else None
    except (OSError, RuntimeError):
        return None


def find_installed_app(steam_dir, app_id):
    """Return one installed app beneath the explicitly supplied Steam location.

    A client or SteamLibrary root includes its known library lists. Supplying a
    ``steamapps`` directory restricts lookup to that one library. Missing or
    ambiguous installs, malformed metadata and unsafe paths raise ServerError.
    """
    app_id = _app_id(app_id)
    matches = []
    for apps in _library_directories(steam_dir):
        installed = _installed_directory(apps, app_id)
        if installed is not None:
            matches.append(installed)
    if not matches:
        raise ServerError("No installed Steam app matches the requested app ID")
    if len(matches) != 1:
        raise ServerError("Steam app is installed in multiple libraries; select one steamapps directory")
    return matches.pop()
