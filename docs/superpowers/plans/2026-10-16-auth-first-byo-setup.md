# Auth-first BYO Setup Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for implementation and review. Steps use checkbox syntax for tracking.

**Goal:** Make authenticated BYO acquisition the preferred setup flow, remember the selected profile, and support explicit Steam-directory imports.

**Architecture:** Reuse private auth and acquisition/import helpers; keep public library discovery in one read-only utility and orchestration in server/assets.py.

**Tech Stack:** Python, pathlib, bounded KeyValues metadata parsing, existing CLI/parser/datastore, pytest.

## 1. Shared cache repair

- [ ] Add synthetic old/new cache-location and login tests; watch new-layout failure.
- [ ] Accept profile/home/Steam/config/config.vdf and legacy runtime/config/config.vdf. Preserve all security checks.
- [ ] Run auth/SteamCMD tests and changed-file pylint; spec and quality review the focused commit.

## 2. Steam library discovery

Create src/utils/steam_library.py and tests/unit_tests/utils/test_steam_library.py. Public API: find_installed_app(steam_dir, app_id) -> pathlib.Path.

- [ ] Tests first for Steam/client roots, explicit steamapps, modern/legacy extra libraries, escaped names, unavailable libraries, missing/duplicate installs, mismatched IDs, traversal and unsafe metadata.
- [ ] Implement bounded quoted KeyValues subset and read-only metadata lookup; no auth files or recursive Steam scans. Use the detailed design's path/source rules.
- [ ] Run focused tests and pylint10; review/commit this independent utility.

## 3. Auth-first setup integration

Modify src/server/server.py, src/server/assets.py, src/utils/steam_auth.py and focused server/auth tests.

- [ ] Write failing real-option-parser and orchestration tests for setup --auth-profile / --steam-dir; options never reach module configure/install.
- [ ] Add keyword-only options and reject conflicting selectors before configure. Reuse one managed Steam source from the recipe, inspect native installed files and acquire only when missing.
- [ ] Add setup orchestration after host/port checks and before module.install. Explicit local sources override remembered profile for one invocation. No source failure fallback.
- [ ] Validate and persist the profile name as steam_auth_profile only after successful file phase, never secrets. Add central set handling for replacement/deletion outside module game settings.
- [ ] Regression coverage: ordinary modules unchanged, valid files no re-download, missing files reuse saved profile, manual-only/ambiguous recipes refuse, running server refusal, unsuccessful acquisition prevents install/persistence, exact local allowlist and immutable source.
- [ ] Run focused tests/pylint; spec and quality review the integration.

## 4. Docs, validation and local handoff

- [ ] Update changelog, BYO/auth/command guides, affected six game helper notes, README and DEVELOPERS in audience order. Preferred examples use setup --auth-profile; installed-library examples are explicit alternatives.
- [ ] Update the 42-row campaign's first-step/queue with actual cache status and new preferred setup path. Never mark acquisition/lifecycle passed from file presence alone.
- [ ] Full unit gate: PYTEST_XDIST_AUTO_NUM_WORKERS=4 make test PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python. Lint: make lint PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python (10.00/10). Use host filesystem for auth UID checks.
- [ ] Final combined review, git diff --check, commit docs and preserve the managed worktree.
- [ ] Validate existing private session presence without reading its contents, then resume only the selected Q3 SSD row if authentication/dependencies permit. Do not start other queue rows in parallel.
