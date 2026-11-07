"""Shared helpers for external mod providers such as GameBanana, Workshop, and direct URLs."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen

from server import ServerError

from .errors import ModSupportError


_GAMEBANANA_ID_RE = re.compile(r"^[0-9]+$")
_WORKSHOP_ID_RE = re.compile(r"^[0-9]+$")
_GAMEBANANA_FILES_API = "https://gamebanana.com/apiv11/Mod/{item_id}?_csvProperties=_aFiles"
_SUPPORTED_ARCHIVE_SUFFIXES = (
    (".7z", "7z"),
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
MODDB_ALLOWED_HOSTS = ("moddb.com", "www.moddb.com")
MTA_COMMUNITY_ALLOWED_HOSTS = ("community.multitheftauto.com",)
_MODDB_PAGE_RE = re.compile(
    r"^https?://(?:www\.)?moddb\.com/(?P<section>(?:mods|games)/[^?#]+/(?P<kind>downloads|addons)/[^/?#]+)(?:[/?#].*)?$",
    re.IGNORECASE,
)
_MODDB_START_RE = re.compile(
    r"https?://(?:www\.)?moddb\.com/(?P<kind>downloads|addons)/start/(?P<download_id>\d+)",
    re.IGNORECASE,
)
_MTA_COMMUNITY_DOWNLOAD_PAGE_RE = re.compile(
    r"(\?p=resources&s=download&resource=(?P<resource_id>\d+)[^\"']*selectincludes=1)",
    re.IGNORECASE,
)
_MTA_COMMUNITY_ASSET_RE = re.compile(
    r"(?P<asset_path>modules/resources/doDownload\.php\?file=(?P<file>[^&\"']+)&name=(?P<name>[^\"']+))",
    re.IGNORECASE,
)


def validate_gamebanana_id(raw_value: str) -> str:
    """Return a normalized GameBanana item id or raise for invalid input."""

    if not _GAMEBANANA_ID_RE.match(str(raw_value)):
        raise ServerError("GameBanana entries require a numeric item id")
    return str(raw_value)


def validate_workshop_id(raw_value: str) -> str:
    """Return a normalized workshop item id or raise for invalid input."""

    if not _WORKSHOP_ID_RE.match(str(raw_value)):
        raise ServerError("Workshop entries require a numeric workshop id")
    return str(raw_value)


def resolve_direct_url_entry(
    raw_value: str,
    *,
    filename: str | None = None,
    allowed_suffixes: dict[str, str],
    entry_label: str,
    filename_description: str,
) -> dict:
    """Resolve and normalize a direct download URL entry."""

    parsed = urlparse(str(raw_value))
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ServerError(f"{entry_label} require an http or https URL")

    resolved_filename = filename or Path(parsed.path).name
    archive_type = _match_allowed_suffix(resolved_filename, allowed_suffixes)
    if not resolved_filename or archive_type is None:
        raise ServerError(f"{entry_label} require {filename_description}")

    digest = hashlib.sha256(str(raw_value).encode("utf-8")).hexdigest()[:12]
    return {
        "source_type": "url",
        "requested_id": str(raw_value),
        "resolved_id": f"url.{digest}.{resolved_filename}",
        "download_url": str(raw_value),
        "filename": resolved_filename,
        "allowed_host": parsed.hostname,
        "archive_type": archive_type,
    }


def resolve_moddb_entry(raw_value: str) -> dict:
    """Resolve a Mod DB downloads/addons page URL to a concrete archive download."""

    page_url = _normalize_moddb_page_url(raw_value)
    page_html = _fetch_text(page_url, raw_value)
    download_kind, download_id, download_url = _extract_moddb_start_url(page_html, raw_value)
    filename = _extract_moddb_filename(page_html, raw_value)
    archive_type = _archive_type_for_name(filename)
    if archive_type is None:
        raise ModSupportError(
            f"Mod DB entry '{raw_value}' does not expose a supported zip or tar archive"
        )
    return {
        "source_type": "moddb",
        "requested_id": page_url,
        "resolved_id": f"moddb.{download_kind}.{download_id}",
        "download_url": download_url,
        "filename": filename,
        "archive_type": archive_type,
    }


def resolve_mta_community_entry(raw_value: str) -> dict:
    """Resolve an MTA community resource detail page to a concrete download flow."""

    detail_page_url, resource_id = _normalize_mta_community_detail_url(raw_value)
    detail_page_html = html.unescape(_fetch_text(detail_page_url, raw_value))
    download_page_match = _MTA_COMMUNITY_DOWNLOAD_PAGE_RE.search(detail_page_html)
    if not download_page_match:
        raise ModSupportError(f"Failed to resolve an MTA community download page for '{raw_value}'")

    download_page_url = urljoin(detail_page_url, download_page_match.group(1))
    download_page_html = html.unescape(_fetch_text(download_page_url, raw_value))
    asset_match = _MTA_COMMUNITY_ASSET_RE.search(download_page_html)
    if not asset_match:
        raise ModSupportError(f"Failed to resolve an MTA community archive for '{raw_value}'")

    filename = Path(asset_match.group("name")).name
    archive_type = _archive_type_for_name(filename)
    if archive_type is None:
        raise ModSupportError(
            f"MTA community entry '{raw_value}' does not expose a supported zip or tar archive"
        )

    resource_name = _normalize_mta_resource_name(Path(filename).stem)
    file_stem = Path(asset_match.group("file")).stem
    return {
        "source_type": "community",
        "requested_id": detail_page_url,
        "resolved_id": f"mtacommunity.{resource_id}.{file_stem}",
        "download_page_url": download_page_url,
        "asset_path": asset_match.group("asset_path"),
        "filename": filename,
        "archive_type": archive_type,
        "resource_name": resource_name,
    }


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


def _fetch_text(url: str, raw_value: str) -> str:
    request = Request(url, headers={"User-Agent": "AlphaGSM/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, OSError, UnicodeDecodeError) as exc:
        raise ModSupportError(f"Failed to query Mod DB entry '{raw_value}': {exc}") from exc


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


def _normalize_moddb_page_url(raw_value: str) -> str:
    match = _MODDB_PAGE_RE.match(str(raw_value).strip())
    if not match:
        raise ServerError(
            "Mod DB entries require a canonical mod or addon page URL under moddb.com"
        )
    return f"https://www.moddb.com/{match.group('section')}"


def _normalize_mta_community_detail_url(raw_value: str) -> tuple[str, str]:
    parsed = urlparse(str(raw_value).strip())
    if parsed.scheme not in ("http", "https") or parsed.hostname not in MTA_COMMUNITY_ALLOWED_HOSTS:
        raise ServerError(
            "MTA community entries require a canonical resource detail page URL under community.multitheftauto.com"
        )

    query = parse_qs(parsed.query)
    if query.get("p", [None])[0] != "resources" or query.get("s", [None])[0] != "details":
        raise ServerError(
            "MTA community entries require a canonical resource detail page URL under community.multitheftauto.com"
        )

    resource_id = query.get("id", [None])[0]
    if resource_id is None or not str(resource_id).isdigit():
        raise ServerError(
            "MTA community entries require a canonical resource detail page URL under community.multitheftauto.com"
        )

    return (
        f"https://community.multitheftauto.com/index.php?p=resources&s=details&id={resource_id}",
        str(resource_id),
    )


def _extract_moddb_start_url(page_html: str, raw_value: str) -> tuple[str, str, str]:
    match = _MODDB_START_RE.search(page_html)
    if not match:
        raise ModSupportError(f"Failed to resolve a Mod DB download link for '{raw_value}'")
    return (
        str(match.group("kind")).lower(),
        match.group("download_id"),
        f"https://www.moddb.com/{match.group('kind').lower()}/start/{match.group('download_id')}",
    )


def _extract_moddb_filename(page_html: str, raw_value: str) -> str:
    lowered = page_html.lower()
    marker_index = lowered.find("filename")
    if marker_index == -1:
        raise ModSupportError(f"Failed to resolve a Mod DB filename for '{raw_value}'")
    search_window = html.unescape(page_html[marker_index : marker_index + 512])
    for suffix, _archive_type in _SUPPORTED_ARCHIVE_SUFFIXES:
        filename_match = re.search(
            rf"([A-Za-z0-9][^<>\n\r\"']+?{re.escape(suffix)})",
            search_window,
            re.IGNORECASE,
        )
        if filename_match:
            return Path(filename_match.group(1).strip()).name
    raise ModSupportError(
        f"Mod DB entry '{raw_value}' does not expose a supported zip or tar archive"
    )


def _normalize_mta_resource_name(raw_value: str) -> str:
    normalized = str(raw_value).replace(".", "_").strip()
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", normalized)
    normalized = normalized.strip("_")
    if not normalized:
        raise ModSupportError("MTA resource name could not be derived from the upstream archive name")
    return normalized


def _archive_type_for_name(file_name: str) -> str | None:
    lower_name = str(file_name).lower()
    for suffix, archive_type in _SUPPORTED_ARCHIVE_SUFFIXES:
        if lower_name.endswith(suffix):
            return archive_type
    return None


def _match_allowed_suffix(file_name: str, allowed_suffixes: dict[str, str]) -> str | None:
    lower_name = str(file_name).lower()
    for suffix, archive_type in allowed_suffixes.items():
        if lower_name.endswith(str(suffix).lower()):
            return archive_type
    return None