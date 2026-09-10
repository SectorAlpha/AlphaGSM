#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_SLUG="${GITHUB_REPOSITORY:-SectorAlpha/AlphaGSM}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-master}"
WIKI_REMOTE="https://x-access-token:${GITHUB_TOKEN:?GITHUB_TOKEN is required}@github.com/${REPO_SLUG}.wiki.git"
WORK_DIR="${WIKI_WORKDIR:-$(mktemp -d)}"
WIKI_DIR="$WORK_DIR/wiki"

cleanup() {
  if [[ -z "${WIKI_WORKDIR:-}" ]]; then
    rm -rf "$WORK_DIR"
  fi
}

trap cleanup EXIT

git clone "$WIKI_REMOTE" "$WIKI_DIR"

python3 - <<'PY' "$REPO_ROOT" "$WIKI_DIR" "$REPO_SLUG" "$DEFAULT_BRANCH"
import os
from pathlib import Path
import re
import sys

repo_root = Path(sys.argv[1])
wiki_dir = Path(sys.argv[2])
repo_slug = sys.argv[3]
default_branch = sys.argv[4]
blob_root = f"https://github.com/{repo_slug}/blob/{default_branch}/"


def to_wiki_name(stem: str) -> str:
    """Convert a file stem to a hyphenated TitleCase wiki page name.

    Examples:
      'minecraft-vanilla' -> 'Minecraft-Vanilla'
      'TEST_STATUS'       -> 'Test-Status'
      'abfserver'         -> 'Abfserver'
    """
    parts = re.split(r"[-_]", stem)
    return "-".join(p.capitalize() for p in parts)


# Fixed mappings for top-level docs and docs/README.md (special names).
page_map = {
    "README.md": "Getting-Started.md",
    "DEVELOPERS.md": "Developers.md",
    "docs/README.md": "Docs.md",
}

link_map = {
    "README.md": "Getting-Started",
    "DEVELOPERS.md": "Developers",
    "docs/README.md": "Docs",
}

# Auto-map every other .md file directly under docs/.
for md_file in sorted((repo_root / "docs").glob("*.md")):
    if md_file.name == "README.md":
        continue
    rel = f"docs/{md_file.name}"
    wiki_name = to_wiki_name(md_file.stem)
    page_map[rel] = f"{wiki_name}.md"
    link_map[rel] = wiki_name

# Auto-map every .md file under docs/servers/.
server_wiki_names: list[str] = []
for md_file in sorted((repo_root / "docs" / "servers").glob("*.md")):
    rel = f"docs/servers/{md_file.name}"
    wiki_name = to_wiki_name(md_file.stem)
    page_map[rel] = f"{wiki_name}.md"
    link_map[rel] = wiki_name
    server_wiki_names.append(wiki_name)

link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def rewrite_links(text: str, source: str) -> str:
    source_dir = Path(source).parent

    def repl(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        resolved = Path(os.path.normpath(source_dir / target)).as_posix()
        if resolved in link_map:
            return f"[[{label}|{link_map[resolved]}]]"
        return f"[{label}]({blob_root}{resolved})"

    return link_pattern.sub(repl, text)


for source, dest in page_map.items():
    content = (repo_root / source).read_text()
    rewritten = rewrite_links(content, source)
    (wiki_dir / dest).write_text(rewritten)

server_guide_lines = "\n".join(
    f"- [[{name.replace('-', ' ')}]]" for name in server_wiki_names
)

home = f"""# AlphaGSM

**Alpha Game Server Manager** — run dedicated servers from a terminal that stays readable under pressure.

Create, set up, start, check, update, and back up game servers on the host or in Docker. This wiki is published from the repository docs; the source of truth is [SectorAlpha/AlphaGSM](https://github.com/SectorAlpha/AlphaGSM).

> The everyday flow is always the same: **Create → Setup → Launch → Verify**.

## Start here

| I want to… | Open |
| --- | --- |
| Install AlphaGSM and run my first server | [[Getting Started]] |
| Pick a game and copy the commands | [[Docs]] |
| Add a new game to AlphaGSM | [[Adding A Game Server]] |
| Change AlphaGSM itself | [[Developers]] |

## Workflow

| Step | Command | What it does |
| --- | --- | --- |
| Create | `alphagsm <name> create <module>` | Register the server |
| Setup | `alphagsm <name> setup` | Download files and write config |
| Launch | `alphagsm <name> start` | Run it on the host or in Docker |
| Verify | `status` / `query` / `info` | Confirm it is actually up |

Then `stop`, `backup`, or `update` as needed.

## Runtimes

Use the host when you need direct control. Use Docker when you want cleaner isolation.

- [[Docker Manager]] — run AlphaGSM itself as a manager container
- [[Docker Runtime Host]] — keep AlphaGSM on the host, launch games in Docker
- `alphagsm <name> doctor` — check backend, image, and container state before `start`

## Support

- [[Game Server Support]] — which servers currently pass
- [[Platform Support]]
- [[Manual Download Fallbacks]]
- [[Test Status]]

## Featured server guides

- [[Minecraft Vanilla]]
- [[Teamfortress2]]
- [[Palworld]]
- [[Hl2dmserver]]

<details>
<summary>All server guides</summary>

{server_guide_lines}

</details>

## Source repository

- [SectorAlpha/AlphaGSM](https://github.com/SectorAlpha/AlphaGSM)
- [Product site](https://alphagsm.sector-alpha.net/)
"""

(wiki_dir / "Home.md").write_text(home)
PY

pushd "$WIKI_DIR" >/dev/null

git config user.name "${GIT_AUTHOR_NAME:-github-actions[bot]}"
git config user.email "${GIT_AUTHOR_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}"

git add .
if git diff --cached --quiet; then
  echo "No wiki changes to publish."
  exit 0
fi

git commit -m "Update wiki from repository docs"
git push origin master

popd >/dev/null
