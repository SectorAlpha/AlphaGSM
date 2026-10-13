"""Game-validated Steam Workshop items and bounded collection expansion."""

from __future__ import annotations

import json
import re
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from .errors import ModSupportError

MAX_WORKSHOP_NODES = 1000
MAX_WORKSHOP_REQUESTS = 128
_API_ROOT = "https://api.steampowered.com/ISteamRemoteStorage"
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def validate_workshop_identifier(value):
    """Require a positive ASCII uint64 Workshop ID before network or disk IO."""
    text = str(value)
    if not re.fullmatch(r"[0-9]{1,20}", text) or not 0 < int(text) < 2**64:
        raise ModSupportError("Steam Workshop entries require a positive numeric workshop id (uint64)")
    return str(int(text))


def normalize_workshop_identifier(value):
    """Accept a numeric ID or an official Steam Community filedetails URL."""
    text = str(value)
    if "://" not in text:
        return validate_workshop_identifier(value)
    try:
        parsed = urlsplit(text.strip())
        if (parsed.scheme not in ("http", "https")
                or parsed.netloc.lower() not in ("steamcommunity.com", "www.steamcommunity.com")
                or parsed.path.rstrip("/") not in ("/sharedfiles/filedetails", "/workshop/filedetails")
                or any(ord(character) < 32 for character in text)):
            raise ValueError("Not a Steam Workshop filedetails URL")
        identifiers = parse_qs(parsed.query, keep_blank_values=True).get("id", [])
        if len(identifiers) != 1:
            raise ValueError("Expected exactly one Workshop ID")
        return validate_workshop_identifier(identifiers[0])
    except ValueError as exc:
        raise ModSupportError("Expected a Workshop ID or Steam Community filedetails URL") from exc


def _post_details(method, ids, result_key):
    """Read bounded public Valve metadata with finite transport retries."""
    count_key = "collectioncount" if method == "GetCollectionDetails" else "itemcount"
    fields = {count_key: len(ids), **{f"publishedfileids[{i}]": value for i, value in enumerate(ids)}}
    request = Request(f"{_API_ROOT}/{method}/v1/", data=urlencode(fields).encode("ascii"))
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise ModSupportError("Steam Workshop response exceeds the size limit")
            records = json.loads(raw)["response"][result_key]
            if not isinstance(records, list):
                raise ValueError("Expected metadata records")
            by_id = {validate_workshop_identifier(record["publishedfileid"]): record for record in records}
            if len(by_id) != len(records) or set(by_id) != set(ids):
                raise ValueError("Missing or unexpected Workshop IDs")
            if any(record.get("result") != 1 for record in records):
                raise ModSupportError("Steam Workshop item or collection is unavailable or inaccessible")
            return by_id
        except (KeyError, TypeError, ValueError, UnicodeError) as exc:
            raise ModSupportError("Invalid Steam Workshop API response") from exc
        except OSError as exc:
            if isinstance(exc, HTTPError) and exc.code != 429 and not 500 <= exc.code < 600:
                raise ModSupportError(f"Steam Workshop API request failed: {exc}") from exc
            if attempt == 2:
                raise ModSupportError(f"Steam Workshop API request failed: {exc}") from exc
            time.sleep(2 ** attempt)
    raise ModSupportError("Steam Workshop API request failed")


class _WorkshopResolver:
    """Cache metadata and limit requests for one atomic resolution operation."""

    def __init__(self, app_id):
        if not re.fullmatch(r"[0-9]{1,10}", str(app_id)) or not 0 < int(app_id) < 2**32:
            raise ModSupportError("Steam Workshop requires a positive game AppID (uint32)")
        self.app_id = int(app_id)
        self.metadata = {}
        self.collections = {}
        self.requests = 0

    def request(self, method, ids, result_key):
        """Account for each bounded metadata request."""
        self.requests += 1
        if self.requests > MAX_WORKSHOP_REQUESTS:
            raise ModSupportError("Steam Workshop collection exceeds the request limit")
        return _post_details(method, ids, result_key)

    def load(self, ids):
        """Fetch uncached IDs in batches, checking the consumer game for all."""
        missing = list(dict.fromkeys(value for value in ids if value not in self.metadata))
        if len(self.metadata) + len(missing) > MAX_WORKSHOP_NODES:
            raise ModSupportError("Steam Workshop collection exceeds the item limit")
        for offset in range(0, len(missing), 100):
            records = self.request("GetPublishedFileDetails", missing[offset:offset + 100], "publishedfiledetails")
            for item_id, record in records.items():
                actual_app = record.get("consumer_app_id")
                if str(actual_app) != str(self.app_id):
                    raise ModSupportError(
                        f"Steam Workshop ID {item_id} belongs to game AppID {actual_app}; expected {self.app_id}"
                    )
                # Valve's legacy RemoteStorage responses omit file_type entirely.
                # Real file content identifies items; otherwise verify collection identity.
                if record.get("file_type") is None:
                    if record.get("file_url") or record.get("hcontent_file") not in (None, "", 0, "0"):
                        record["file_type"] = 0
                    else:
                        collection = self.request("GetCollectionDetails", [item_id], "collectiondetails")[item_id]
                        self.collections[item_id] = collection
                        record["file_type"] = 2
                if record.get("file_type") not in (0, 2):
                    raise ModSupportError(f"Steam Workshop ID {item_id} is not a downloadable item or collection")
            self.metadata.update(records)

    def children(self, collection_id):
        """Read validated collection child IDs before traversal."""
        if collection_id not in self.collections:
            self.collections[collection_id] = self.request("GetCollectionDetails", [collection_id], "collectiondetails")[collection_id]
        record = self.collections[collection_id]
        children = record.get("children")
        if not isinstance(children, list) or not children:
            raise ModSupportError(f"Steam Workshop collection {collection_id} is empty or invalid")
        try:
            ids = [validate_workshop_identifier(child["publishedfileid"]) for child in children]
        except (KeyError, TypeError) as exc:
            raise ModSupportError("Invalid Steam Workshop collection children") from exc
        self.load(ids)
        return ids


def resolve_workshop_item(item_id, app_id):
    """Resolve an individual downloadable item belonging to the expected game."""
    return resolve_workshop_items([item_id], app_id)[0]


def resolve_workshop_items(item_ids, app_id):
    """Validate a batch of items under one shared node/request budget."""
    item_ids = list(dict.fromkeys(normalize_workshop_identifier(value) for value in item_ids))
    resolver = _WorkshopResolver(app_id)
    resolver.load(item_ids)
    entries = []
    for item_id in item_ids:
        if resolver.metadata[item_id]["file_type"] != 0:
            raise ModSupportError(f"Steam Workshop ID {item_id} is a collection; use workshop-collection")
        entries.append({"workshop_id": item_id, "source_type": "workshop", "resolved_id": f"workshop.{item_id}"})
    return entries


def resolve_workshop_collection(collection_id, app_id):
    """Expand a same-game collection, preserving order without cycles or duplicates."""
    collection_id = normalize_workshop_identifier(collection_id)
    resolver = _WorkshopResolver(app_id)
    resolver.load([collection_id])
    if resolver.metadata[collection_id]["file_type"] != 2:
        raise ModSupportError(f"Steam Workshop ID {collection_id} is not a collection")
    stack = [(collection_id, False)]
    active, visited = set(), set()
    items = []
    while stack:
        item_id, leaving = stack.pop()
        if leaving:
            active.remove(item_id)
            visited.add(item_id)
            continue
        if item_id in active:
            raise ModSupportError(f"Steam Workshop collection cycle at {item_id}")
        if item_id in visited:
            continue
        if resolver.metadata[item_id]["file_type"] == 0:
            visited.add(item_id)
            items.append(item_id)
            continue
        active.add(item_id)
        stack.append((item_id, True))
        stack.extend((child, False) for child in reversed(resolver.children(item_id)))
    if not items:
        raise ModSupportError(f"Steam Workshop collection {collection_id} is empty")
    return items
