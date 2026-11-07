---
name: server-support-tracker
description: 'Track AlphaGSM game server support status, disabled-server triage, active-vs-supported drift, and next non-auth candidates. Use when asked how many games work now, what is left, which disabled reasons are stale, or which server slice to tackle next.'
user-invocable: true
---

# Server Support Tracker

Use this skill when you need a current snapshot of AlphaGSM server support and a repeatable way to decide what to work on next.

## Primary Sources

- `docs/game-server-support.md` for the published supported vs unsupported snapshot.
- `docs/module_parity_report.md` for active vs disabled module state.
- `docs/TEST_STATUS.md` for the current reason a server is blocked.
- `disabled_servers.conf` for hard-disabled modules and the exact gate reason.
- `tests/smoke_tests/` and `tests/integration_tests/` for the real lifecycle coverage surface.

## Procedure

1. Run the bundled snapshot script:
   `bash .github/skills/server-support-tracker/scripts/support_snapshot.sh`
   For machine-readable output:
   `bash .github/skills/server-support-tracker/scripts/support_snapshot.sh --json`
2. Read the summary in this order:
   - supported vs unsupported counts
   - active vs disabled module counts
   - active-but-unchecked drift between parity and support docs
   - unsupported-but-not-disabled candidates
   - disabled blocker buckets
3. If you need a ranked next-work list for non-auth modules, run:
   `bash .github/skills/server-support-tracker/scripts/rank_candidates.sh`
   This favors modules that are already active or only prerequisite-gated over hard-disabled crash/auth cases.
4. Prioritize work in this order unless the user says otherwise:
   - current CI failures
   - unsupported but not disabled modules
   - hard-disabled non-auth modules with stale or repairable download/runtime reasons
   - auth-gated SteamCMD modules last
5. Before re-enabling a disabled module, confirm the real blocker locally and then update the lifecycle/docs in the repository order from `AGENTS.md`.

## Output Interpretation

- `Supported now` is the published snapshot from `docs/game-server-support.md`.
- `Active modules` is broader and can include prerequisite-gated modules that are not fully working yet.
- `Active but unchecked` is the drift list to inspect before quoting counts as final.
- `Unsupported but not disabled` is the main backlog for modules that are not hard-blocked by `disabled_servers.conf`.

## Notes

- The snapshot script is read-only and safe to run repeatedly.
- Use `--all` with the scripts to print the full actionable lists instead of the default trimmed view.
- If a module moves from disabled to active, update smoke tests, changelog, server guide, and status docs in the repo-prescribed order.

## Bundled Tool

- [support snapshot script](./scripts/support_snapshot.sh)
- [rank candidates script](./scripts/rank_candidates.sh)