# Wiki Publishing

| Field | Value |
| --- | --- |
| Purpose | Mirror tracked repository docs into the GitHub wiki safely. |
| Use when | Changing wiki sync behaviour or adding mirrored docs. |
| Main source | `scripts/publish_wiki.sh`, wiki workflow, and tracked docs. |

| Field | Value |
| --- | --- |
| Inputs | Repository docs, page mapping, link rewriting rules, wiki workflow. |
| Outputs | Updated wiki sync script, updated mirrored pages, and working wiki links. |
| Related files | `scripts/publish_wiki.sh`, `.github/workflows/wiki-sync.yaml`, `README.md`, `DEVELOPERS.md`, `docs/**`. |

Use this skill when changing how repository documentation is mirrored into the GitHub wiki.

## Source Of Truth

The repository documentation is the source of truth.

Primary source files:

- `README.md`
- `DEVELOPERS.md`
- `docs/README.md`
- `docs/servers/*.md`

## Files To Inspect

- `scripts/publish_wiki.sh`
- `.github/workflows/wiki-sync.yaml`
- `README.md`
- `DEVELOPERS.md`
- `docs/`

## Rules

- Prefer updating repository docs first.
- Treat the wiki as a published mirror, not the primary authoring location.
- Keep wiki page names stable where possible.
- Preserve or rewrite links so they work in the wiki context.

## When To Update

If docs change substantially or new top-level guides are added, update:

- the publish script page map
- the link rewrite map
- the generated wiki home page
