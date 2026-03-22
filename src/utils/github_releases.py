"""Helpers for resolving downloadable assets from GitHub releases."""

import json
import urllib.parse
import urllib.request

from server import ServerError

HTTP_USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"


def read_json(url):
    """Fetch and parse JSON from a URL using AlphaGSM's user agent."""

    request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_release_asset(api_url, asset_matcher, version=None):
    """Resolve a release asset matching a caller-supplied predicate."""

    if version not in (None, "", "latest"):
        api_url = api_url.rsplit("/", 1)[0] + "/tags/" + urllib.parse.quote(str(version), safe="")
    release_data = read_json(api_url)
    for asset in release_data.get("assets", []):
        if asset_matcher(asset):
            return release_data.get("tag_name"), asset["browser_download_url"]
    raise ServerError("Unable to locate a suitable release asset")


def resolve_latest_release_asset(api_url, asset_matcher):
    """Resolve the latest release asset matching a caller-supplied predicate."""

    return resolve_release_asset(api_url, asset_matcher, version="latest")
