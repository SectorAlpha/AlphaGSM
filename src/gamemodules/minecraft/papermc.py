"""Helpers for PaperMC-family downloads such as Paper, Velocity, and Waterfall."""

import json
import re
import urllib.request

from server import ServerError

PAPERMC_API_ROOT = "https://fill.papermc.io/v3"
PAPERMC_USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"


def _version_sort_key(version):
    """Return a sort key that places newer semantic-like versions first."""

    return tuple(
        (0, int(token)) if token.isdigit() else (1, token)
        for token in re.split(r"([0-9]+)", version)
        if token
    )


def _read_json(url):
    """Fetch a JSON document from the PaperMC downloads service."""

    request = urllib.request.Request(url, headers={"User-Agent": PAPERMC_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_versions(project_data):
    """Flatten the project version listing returned by the PaperMC API."""

    versions = project_data.get("versions", {})
    if isinstance(versions, dict):
        all_versions = []
        for entries in versions.values():
            all_versions.extend(entries)
        return all_versions
    if isinstance(versions, list):
        return list(versions)
    return []


def _get_download_url(build):
    """Return the best download URL from a PaperMC build payload."""

    downloads = build.get("downloads", {})
    preferred_key = next(
        (key for key in downloads if key.endswith(":default")),
        None,
    )
    if preferred_key is None:
        preferred_key = next(iter(downloads), None)
    if preferred_key is None:
        return None
    return downloads[preferred_key].get("url")


def resolve_download(project, version=None):
    """Resolve the latest stable PaperMC-family download URL for a project."""

    project_data = _read_json("%s/projects/%s" % (PAPERMC_API_ROOT, project))
    versions = _extract_versions(project_data)
    if not versions:
        raise ServerError("No versions available for project '%s'" % (project,))
    candidate_versions = (
        [version]
        if version not in (None, "", "latest")
        else sorted(set(versions), key=_version_sort_key, reverse=True)
    )

    for candidate in candidate_versions:
        builds = _read_json(
            "%s/projects/%s/versions/%s/builds" % (PAPERMC_API_ROOT, project, candidate)
        )
        for build in builds:
            if build.get("channel") != "STABLE":
                continue
            download_url = _get_download_url(build)
            if download_url is not None:
                return candidate, download_url

    if version not in (None, "", "latest"):
        raise ServerError(
            "No stable build found for project '%s' version '%s'" % (project, version)
        )
    raise ServerError("No stable builds found for project '%s'" % (project,))


def get_start_command(server):
    """PaperMC helper module does not provide a runtime start command.

    This helper exists to resolve downloads only. Calling `get_start_command`
    here will raise to indicate it's not a runnable module.
    """
    raise NotImplementedError("PaperMC helper is not a runnable gamemodule")


def get_runtime_requirements(server):
    """PaperMC helper does not provide runtime metadata."""
    raise NotImplementedError("PaperMC helper is not a runnable gamemodule")


def get_container_spec(server):
    """PaperMC helper does not provide a container launch spec."""
    raise NotImplementedError("PaperMC helper is not a runnable gamemodule")
