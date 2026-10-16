# Auth-first BYO Setup Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for implementation and review. Steps use checkbox syntax for tracking.

**Goal:** Make authenticated BYO acquisition the preferred setup flow, remember the selected profile, and support explicit Steam-directory imports.

**Architecture:** Reuse private auth and acquisition/import helpers; keep public library discovery in one read-only utility and orchestration in server/assets.py.

**Tech Stack:** Python, pathlib, bounded KeyValues metadata parsing, existing CLI/parser/datastore, pytest.

## 1. Shared cache repair

- [x] Add synthetic old/new cache-location and login tests; watch new-layout failure.
- [x] Accept profile/home/Steam/config/config.vdf and legacy runtime/config/config.vdf. Preserve all security checks.
- [x] Run auth/SteamCMD tests and changed-file pylint; spec and quality review the focused commit.

## 2. Steam library discovery

Create src/utils/steam_library.py and tests/unit_tests/utils/test_steam_library.py. Public API: find_installed_app(steam_dir, app_id) -> pathlib.Path.

- [x] Tests first for Steam/client roots, explicit steamapps, modern/legacy extra libraries, escaped names, unavailable libraries, missing/duplicate installs, mismatched IDs, traversal and unsafe metadata.
- [x] Implement bounded quoted KeyValues subset and read-only metadata lookup; no auth files or recursive Steam scans. Use the detailed design's path/source rules.
- [x] Run focused tests and pylint10; review/commit this independent utility. 104 tests; spec and quality approved at `4e9303b1`.

## 3. Auth-first setup integration

Modify src/server/server.py, src/server/assets.py, src/utils/steam_auth.py and focused server/auth tests.

- [x] Write failing real-option-parser and orchestration tests for setup --auth-profile / --steam-dir; options never reach module configure/install.
- [x] Add keyword-only options and reject conflicting selectors before configure. Reuse one managed Steam source from the recipe, inspect native installed files and acquire only when missing.
- [x] Add setup orchestration after host/port checks and before module.install. Explicit local sources override remembered profile for one invocation. No source failure fallback.
- [x] Validate and persist the profile name as steam_auth_profile only after successful file phase, never secrets. Add central set handling for replacement/deletion outside module game settings.
- [x] Regression coverage: ordinary modules unchanged, valid files no re-download, missing files reuse saved profile, manual-only/ambiguous recipes refuse, running server refusal, unsuccessful acquisition prevents install/persistence, exact local allowlist and immutable source.
- [x] Run focused tests/pylint; spec and quality review the integration.

## 4. Docs, validation and local handoff

- [x] Update changelog, BYO/auth/command guides, affected six game helper notes, README and DEVELOPERS in audience order. Preferred examples use setup --auth-profile; installed-library examples are explicit alternatives.
- [x] Update the 42-row campaign's first-step/queue with actual cache status and new preferred setup path. Never mark acquisition/lifecycle passed from file presence alone.
- [x] Full unit gate: PYTEST_XDIST_AUTO_NUM_WORKERS=4 make test PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python. Lint: make lint PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python (10.00/10). Use host filesystem for auth UID checks. Verified 10,228 passed / 4 skipped; pylint 10.00/10; 35 skills valid.
- [x] Final combined review, git diff --check, commit docs and preserve the managed worktree.
- [x] Validate existing private session presence without reading its contents, then resume only the selected Q3 SSD row if authentication/dependencies permit. Do not start other queue rows in parallel.

Selected Q3 outcome: authenticated setup/file checks/repeat setup/native Quake UDP lifecycle passed; stopped process and UDP port release verified. Docker NOT_RUN. RTCW remains next; other 41 rows not executed.

## 5. Complete server content and dedicated engine payload

- [x] Add failing shared archive and Q3 install tests for exact relative-file exclusions, preserved server libraries/game modules, all maps/PK3 content, unchanged source and unchanged default behavior for other modules.
- [x] Add optional exact exclusions to shared archive copying/install; declare Q3 known client-only engine paths at module scope and pass them during install. Preserve existing files and never prune unknown operator content.
- [x] Focused tests/lint, spec and quality review, commit implementation.
- [x] Record reusable complete-server-content policy in the all-42 campaign and guides; distinguish minimum sentinel validation from complete installed content.
- [x] Recreate only campaign-generated engine payload on the SSD using the new setup code, retain all owned PK3 content, rerun real native lifecycle and verify shutdown. Record map count, file selection and results.
- [x] Fresh full unit/lint gates and final combined review/commit docs.

Final verification at `a1e2aebb`: 10,235 unit tests passed / 4 skipped, production pylint 10.00/10 and 35 skills valid. A reproduced auth test fixture import-order mismatch was corrected without production/security changes. Dedicated-only Q3 reinstall kept all nine PK3 hashes and 36 maps, omitted 11 client-only engine files, and passed repeated native query/info/shutdown; temporary prior-engine backup removed. Final combined review approved.
