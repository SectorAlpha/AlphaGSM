# BYO files and private SteamCMD sessions implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development for independent tasks and review. All live Steam/game validation is unavailable; tests use synthetic files and mock SteamCMD.

**Goal:** Give file-based BYO modules actionable, game-specific requirements and optional authenticated acquisition, with private reusable SteamCMD sessions.

**Architecture:** Package-local asset manifests describe files, sources and import support through `get_asset_requirements(server)`. Shared inspection/reporting uses that metadata and preserves the existing importer. A separate SteamCMD session-profile helper owns cached authentication, and explicit acquisition downloads to temporary staging before allowlisted import.

**Tech Stack:** Python 3.10, pytest, existing SteamCMD and asset-import modules, POSIX filesystem permissions.

## Baseline and isolation

- [x] Create an isolated worktree on `codex/byo-file-helpers`.
- [x] Copy existing Reclaimer/asset-import changes as a baseline without editing the active checkout.
- [x] Baseline offline asset-import, asset-command and SteamCMD tests: 79 passed.
- [x] Preserve a local baseline snapshot so new changes are distinguishable from existing work.

## Task 1: Private SteamCMD session profiles

Files: create `src/utils/steam_auth.py`, `src/core/steam_auth.py`, `tests/unit_tests/utils/test_steam_auth.py`; modify `src/utils/steamcmd.py`, `src/core/main.py`, `alphagsm.conf-template`, `docs/steamcmd-auth.md`.

- [x] Write failing tests for safe profile names, owner-only storage, link rejection, session-only login arguments, missing/expired-session failures, safe status and local logout. Use temporary directories and fake subprocesses, never real credentials.
- [x] Expose `login(name, username)`, `status(name)`, `logout(name)` and a context manager for a locked profile runtime. Profiles use their own SteamCMD runtime, not a desktop Steam home. Username metadata has mode 0600; profile directories mode 0700. Reject unexpected owners, unsafe links and non-Linux hosts.
- [x] Add top-level dispatch for `steam-auth login PROFILE USERNAME`, `steam-auth status PROFILE`, `steam-auth logout PROFILE`. Interactive SteamCMD owns password/Steam Guard prompts. No password is retained or placed in argv. Noninteractive use disables prompts and never downgrades to anonymous.
- [x] Add optional `auth_profile=None` to `steamcmd.download`; when set, select the isolated runtime and cached login. Serialize access to a profile and keep all nested session files private even after failures. Existing anonymous downloads remain compatible.
- [x] Ensure failure messages and status do not expose cached tokens, passwords, raw session content or credential-bearing command lists. Explain that local logout does not revoke Valve sessions.
- [x] Run `PYTHONPATH=.:src python3 -m pytest tests/unit_tests/utils/test_steam_auth.py tests/unit_tests/utils/test_steamcmd.py -q` and focused core CLI tests.

## Task 2: Per-game file contracts and inspection

Files: create `src/utils/byo_files.py`, package-local `byo_assets.json` manifests for the 42 file-based BYO modules, and `tests/unit_tests/utils/test_byo_files.py`; add module hooks in the matching `main.py` or existing family helper.

- [x] Write a failing catalogue test enumerating `enabled_byo_servers.conf`: all file-based modules except endpoint/service/entitlement-only rows must expose a source-aware recipe. Do not classify auth-only requirements as files.
- [x] Recipe metadata includes `module`, `description`, `sources`, `requirements`, `managed_import`, and the existing importer keys when supported. Each source has an explicit kind and actionable instructions; use authoritative links or an honest manual/unavailable source condition.
- [x] Use requirements shaped like `{"path": "etmain/pak0.pk3", "kind": "file", "nonempty": true}`. Support `file`, `glob`, `directory` and archive-member requirements; alternatives are an explicit group of paths. Preserve custom native validators for richer game semantics.
- [x] Resolve per-instance config paths, executable names, map selection and external game roots. Never interpolate secret values into public recipe reports. Reject unsafe relative paths in manifests.
- [x] Add read-only inspection returning `ready`, `missing`, `requirements`, `sources`, `validation` and `managed_import`. Directory/map/executable sentinels must be labeled as such and cannot be advertised as game readiness.
- [x] Complete the game inventory in the design: owned base data, complete mod trees, client exports, staged server distributions and provider-generated config. Keep secret-bearing and unmodeled full-tree imports explicitly manual.
- [x] Add SteamCMD source app/platform metadata only for sources established by upstream documentation. Tests prove argument selection, not access rights or publisher download support.
- [x] Run synthetic inspection tests and the existing game-module tests affected by hook additions.

## Task 3: Requirements and explicit acquisition commands

Files: modify `src/server/assets.py`, `src/server/server.py`, `src/server/module_contract.py`; create `src/utils/byo_acquire.py` and `tests/unit_tests/utils/test_byo_acquire.py`; extend `tests/unit_tests/server/test_assets.py`.

- [x] Write failing tests for `assets requirements --json`, source-guided checks, unsupported import rejection and stopped-server acquisition guard.
- [x] Extend the existing assets action dispatch with `requirements` and `fetch SOURCE_ID --auth-profile PROFILE`; preserve `check`, `import`, `export`, and setup imports. Reports must remain compatible with existing Reclaimer recipes.
- [x] In `byo_acquire.acquire(server, recipe, source_id, auth_profile=None)`, choose a declared SteamCMD source, require a profile when appropriate, create temporary staging, call `steamcmd.download` with exact app/branch/platform, then call the existing `import_assets` with only the declared import recipe. Remove staging on any outcome and retain destination rollback protections.
- [x] Reject non-SteamCMD sources with actionable acquisition guidance rather than guessing download behavior. Reject recipes that cannot be safely expressed by the current importer. SteamCMD may transfer a full app/depot; only selected files are published.
- [x] Test end-to-end filesystem acquisition with a fake downloader that writes allowed and unrelated files; assert only allowed files reach the destination and staging disappears after success and exceptions. No live authentication is attempted.

## Task 4: Documentation, review and validation

Files: update `DEVELOPERS.md`, `docs/commands.md`, affected server guides, `changelog.txt`, and the design's secure-storage section.

- [x] Document recipe ownership, mandatory/optional files, source instructions, configured paths, session-only auth setup and explicit acquisition. Use actual CLI syntax.
- [x] State the evidence boundary: Linux synthetic tests prove helper behavior; authenticated login/downloads, entitlement, Windows execution and real game readiness remain unverified.
- [x] Run focused tests, `make test`, and `make lint` (10.00/10). Do not launch live Steam/game integration or smoke without the required assets/session. Existing unrelated failures must be identified rather than hidden.
- [x] Review spec compliance, then code quality/security; fix findings and rerun relevant checks.
- [x] Produce a reviewable diff relative to the copied baseline, preserving concurrent root-checkout work. Do not publish or merge a PR without a request.

## Verified outcome

- Full unit gate using the repository dependency environment: 9,995 passed, 4 skipped.
- Full lint gate: 10.00/10; 35 skill metadata/discovery contracts validated.
- Skill-specific regression tests: 24 passed.
- Spec and code-quality reviews passed after fixing their confirmed findings.
- Actual CLI verified with one disposable Q3 metadata instance: requirements JSON,
  configured destination, declared missing-file JSON and local auth status.
- No Steam installation, authentication, app download, game process or live
  integration ran. CI integration is explicitly deferred at the user's request.
- A private local configuration and login handoff are preserved under ignored
  `.local-tests/`; cached auth will live outside this group-writable checkout.
- Concurrent Reclaimer baseline changes were copied and separately snapshotted;
  the active source checkout was not modified by this implementation.
