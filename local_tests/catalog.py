"""Read the tracked AUTH and BYO support lists. This module stores no secrets."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTH_LIST = REPO_ROOT / "enabled_auth_servers.conf"
BYO_LIST = REPO_ROOT / "enabled_byo_servers.conf"


def load_status_file(path):
    """Return module, category, and reason rows from a support list."""

    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3 or not parts[0].strip() or not parts[1].strip():
            raise ValueError("%s:%s is not module, category, reason" % (path, line_number))
        rows.append({
            "module": parts[0].strip(),
            "category": parts[1].strip(),
            "reason": "\t".join(parts[2:]).strip(),
            "line": line_number,
        })
    if not rows:
        raise ValueError("No servers listed in " + str(path))
    return tuple(rows)


def auth_servers():
    """Return ENABLED (AUTH) servers."""

    return load_status_file(AUTH_LIST)


def byo_servers():
    """Return ENABLED (BYO) servers."""

    return load_status_file(BYO_LIST)


def selected_servers(suite, requested):
    """Return rows for one local run.

    ``requested`` is ``all`` or a comma-separated module list. An empty request
    selects nothing so an integration run cannot download every server.
    """

    if suite not in {"auth", "byo", "all"}:
        raise ValueError("Unknown local suite: " + suite)
    wanted = None if requested == "all" else {
        item.strip() for item in requested.split(",") if item.strip()
    }
    rows = []
    if suite in {"auth", "all"}:
        rows.extend(dict(row, suite="auth") for row in auth_servers())
    if suite in {"byo", "all"}:
        rows.extend(dict(row, suite="byo") for row in byo_servers())
    if wanted is None:
        return tuple(rows)
    return tuple(row for row in rows if row["module"] in wanted)
