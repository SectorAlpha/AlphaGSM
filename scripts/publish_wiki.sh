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

page_map = {
    "README.md": "Getting-Started.md",
    "DEVELOPERS.md": "Developers.md",
    "docs/README.md": "Docs.md",
    "docs/servers/minecraft-vanilla.md": "Minecraft-Vanilla.md",
    "docs/servers/team-fortress-2.md": "Team-Fortress-2.md",
    "docs/servers/counter-strike-global-offensive.md": "Counter-Strike-Global-Offensive.md",
}

link_map = {
    "README.md": "Getting-Started",
    "DEVELOPERS.md": "Developers",
    "docs/README.md": "Docs",
    "docs/servers/minecraft-vanilla.md": "Minecraft-Vanilla",
    "docs/servers/team-fortress-2.md": "Team-Fortress-2",
    "docs/servers/counter-strike-global-offensive.md": "Counter-Strike-Global-Offensive",
}

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

home = """# AlphaGSM Wiki

This wiki is published from the main repository documentation.

## Start Here

- [[Getting Started]]
- [[Docs]]
- [[Developers]]

## Server Guides

- [[Minecraft Vanilla]]
- [[Team Fortress 2]]
- [[Counter-Strike Global Offensive]]

## Source Repository

- [SectorAlpha/AlphaGSM](https://github.com/SectorAlpha/AlphaGSM)
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
