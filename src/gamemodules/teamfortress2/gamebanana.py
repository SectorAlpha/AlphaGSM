"""Helpers for resolving TF2 GameBanana downloads by item id."""

from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from server import ServerError
from server.modsupport.errors import ModSupportError


_GAMEBANANA_ID_RE = re.compile(r"^[0-9]+$")
_GAMEBANANA_FILES_API = "https://gamebanana.com/apiv11/Mod/{item_id}?_csvProperties=_aFiles"
_SUPPORTED_ARCHIVE_SUFFIXES = (
    (".tar.gz", "tar"),
    (".tgz", "tar"),
    (".tar.bz2", "tar"),
    (".tbz2", "tar"),
    (".tar.xz", "tar"),
    (".txz", "tar"),
    (".tar", "tar"),
    (".zip", "zip"),
)

GAMEBANANA_ALLOWED_HOSTS = ("gamebanana.com",)


def validate_gamebanana_id(raw_value: str) -> str:
    """Return a normalized GameBanana item id or raise for invalid input."""

    if not _GAMEBANANA_ID_RE.match(str(raw_value)):
        raise ServerError("GameBanana entries require a numeric item id")
    return str(raw_value)


def resolve_gamebanana_mod(raw_value: str) -> dict:
    """Resolve a GameBanana mod id to a concrete downloadable archive."""

    item_id = validate_gamebanana_id(raw_value)
    payload = _fetch_json(_GAMEBANANA_FILES_API.format(item_id=item_id), item_id)
    files = payload.get("_aFiles") or []
    selected = _select_installable_file(item_id, files)
    return {
        "source_type": "gamebanana",
        "requested_id": item_id,
        "resolved_id": f"gamebanana.{item_id}.{selected['_idRow']}",
        "file_id": str(selected["_idRow"]),
        "download_url": selected["_sDownloadUrl"],
        "archive_type": selected["archive_type"],
        "filename": selected["_sFile"],
    }


def _fetch_json(url: str, item_id: str) -> dict:
    request = Request(url, headers={"User-Agent": "AlphaGSM/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        raise ModSupportError(f"Failed to query GameBanana item '{item_id}': {exc}") from exc


def _select_installable_file(item_id: str, files: list[dict]) -> dict:
    candidates = []
    for file_info in files:
        if file_info.get("_bIsArchived"):
            continue
        if not file_info.get("_bHasContents", False):
            continue
        if str(file_info.get("_sAvResult", "")).lower() == "infected":
            continue
        archive_type = _archive_type_for_name(file_info.get("_sFile", ""))
        if archive_type is None:
            continue
        candidate = dict(file_info)
        candidate["archive_type"] = archive_type
        candidates.append(candidate)

    if not candidates:
        raise ModSupportError(
            f"GameBanana item '{item_id}' does not expose a supported zip or tar archive"
        )

    candidates.sort(
        key=lambda entry: (int(entry.get("_tsDateAdded", 0)), int(entry.get("_idRow", 0))),
        reverse=True,
    )
    return candidates[0]


def _archive_type_for_name(file_name: str) -> str | None:
    lower_name = str(file_name).lower()
    for suffix, archive_type in _SUPPORTED_ARCHIVE_SUFFIXES:
        if lower_name.endswith(suffix):
            return archive_type
    return None