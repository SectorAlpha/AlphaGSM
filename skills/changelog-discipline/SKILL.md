# Changelog Discipline

| Field | Value |
| --- | --- |
| Purpose | Keep `changelog.txt` accurate for every PR that changes release-relevant behaviour. |
| Use when | Updating user-visible behaviour, server support, CI, packaging, release process, defaults, or workflow expectations. |
| Main source | `changelog.txt`, `git log`, `AGENTS.md`, changed files in the PR. |

Use this skill whenever a PR changes anything a release note should mention.

## Required Outcome

Update `changelog.txt` in the same PR when changes affect:

- user-facing commands or defaults
- game-server support or disabled-server status
- CI or release workflows
- packaging or binary distribution
- documentation that changes recommended operator behaviour

## Format

Keep `changelog.txt` as plain text.

- Add new entries at the top under the current date.
- Keep each entry short and concrete.
- Mention the affected area first, then the change.
- Prefer factual wording over marketing language.

Example:

```
2026-04-15
- CI: add binary build smoke jobs for Linux, macOS, and Windows artifacts.
- Integration tests: default local scratch root to /media/.../useme when available.
- Server support: re-enable minecraft.bedrock after the official Linux download page exposed a direct archive URL again.
```

## Backfill Rules

- Backfill historical sections from `git log` instead of inventing summaries.
- Prefer first-parent mainline history when reconstructing past milestones.
- Keep raw commit subjects when no better release summary exists.

## Don’ts

- Do not leave release-significant PRs without a changelog update.
- Do not rewrite old history unless it is clearly wrong.
- Do not bury CI or packaging changes just because users do not see them directly.