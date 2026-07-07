# AlphaGSM Improvement Roadmap

Last updated: 2026-06-27

This document is a handoff-oriented review of the whole repository. It lists
concrete improvements a future agent or contributor can pick up, ordered by
theme and rough priority. Read `AGENTS.md` first — it defines the contracts
(lifecycle, port manager, config sync, container runtime, changelog) that any
work here must respect.

## Current State Snapshot

- ~233 game modules under `src/gamemodules/`, package-backed layout.
- Support tracker (`docs/TEST_STATUS.md`): 146 PASSED, 47 ENABLED (AUTH),
  41 ENABLED (BYO), 3 DISABLED, 0 SKIPPED (last updated 2026-06-27; CI now
  enforces parity with the live enabled/disabled gate files).
- Six shared Docker runtime families (`java`, `quake-linux`, `service-console`,
  `simple-tcp`, `steamcmd-linux`, `wine-proton`) with image scaffolds under
  `docker/` and defaults in `src/server/runtime.py`.
- CI: GitHub Actions on `release_v1` runs lint, unit, coverage, binary build
  smoke (3 OS), ~39 smoke batches, ~40 integration batches, plus dedicated
  `slow-*` single-test heavy lanes and backend Docker tests.
- Active campaign: migrating stale host-process (`screen`) integration/smoke
  lanes onto the modules' declared Docker runtime families, then fixing the
  launch-path drift that surfaces.

### In-flight work (as of this writing)

- CI run `27216122584` (commit `ed21dab`) was in progress: it carries the
  btserver/valheim Docker integration switch, hardened native Docker launch
  resolution for `btserver`/`valheim`/`palworld`, and repaired aggregate unit
  expectations. If it failed, start there.
- The local worktree contains a large set of uncommitted modifications
  (~200 files: many `src/gamemodules/*/main.py`, matching `*_cov.py` tests,
  shared utils, scripts). These appear to be a broad in-progress refactor —
  do **not** discard or blanket-commit them; review what they change first.
- `tests/integration_tests/test_btserver.py` and `test_valheim.py` still wait
  on the `a2s` info protocol; whether A2S actually comes up under the Docker
  lane is unproven (todo: "Investigate btserver valheim A2S"). The readiness
  protocol may need to drop to `tcp`/`udp` like other Docker-migrated lanes.

## 1. CI and Test Infrastructure

1. **Done: deduplicate `resolve_steamcmd_linux_runtime_image()` /
   `resolve_wine_proton_runtime_image()`.** The same ~20-line helper was
   copy-pasted into 40+ files under `tests/integration_tests/`; it now lives
   in `tests/integration_tests/conftest.py`, which removes a large drift
   surface.
2. **Audit remaining host-process integration lanes.** Several tests still use
   `require_command("screen")` and `write_config(...)` without
   `runtime_backend=`/`module_name=` while their module declares a Docker
   family. The runtime doctor output in CI ("Configured backend: process /
   Module runtime preference: docker") is the tell. Migrate them the same way
   btserver/valheim were migrated, one lane per PR, and watch the resulting
   launch-path failures.
3. **Done: make `start` failures self-diagnosing in CI.** The integration
   helper now dumps the computed runtime doctor details — command, working
   directory, mounts, and ports — when a start path fails.
4. **Done: stabilize CI monitoring tooling.** `scripts/ci_status.py` now
   polls `gh run view <id> --json status,conclusion,jobs`, prints a compact
   summary, and surfaces failed jobs plus useful log excerpts when a run ends
   red.
5. **Triage the broad red integration batches.** Run `27191687264` showed many
   `batch-N-of-40` failures beyond the touched lanes. Some greps for failure
   signatures returned nothing, so the failure mode there is still
   uncharacterized. Sample 2–3 batch logs end-to-end and classify: shared
   regression vs. pre-existing flaky lanes vs. infra (runner image, port
   collisions).
6. **Done: smoke runner drift.** `tests/smoke_tests/run_btserver.sh` and
   `run_valheim.sh` now follow the Docker SteamCMD pattern instead of the
   host-process `screen` flow, so the smoke canonical lifecycle matches the
   newer integration lanes again.

## 2. Runtime / Module Contract

1. **Done: promote `_resolve_executable_path()` to a shared helper.** The
   symlink-aware, nested-tree executable resolver now lives in
   `src/utils/gamemodules/common.py` as `resolve_install_executable(server, ...)`
   and `btserver`, `valheim`, and the Palworld launcher flow now share it.
2. **Done: host-path leakage into container commands.** Valheim's
   `-savedir` was passing an absolute host path into the container; the fix
   rewrites it relative for Docker. The follow-up audit also corrected
   Vintage Story, Wolf ET, Quake Live, NS2, NS2: Combat, TF2C, Terraria,
   ACC, Arma Reforger, Core Keeper, MOHAA, Mumble, Onset, and V Rising.
   `tests/unit_tests/test_runtime_contract_static.py` now guards the Docker
   command surface so install-dir leaks fail fast.
3. **Verify the A2S surface for Docker btserver/valheim.** Both modules
   publish `queryport` udp+tcp, but the Docker lane has not yet proven A2S
   readiness. If A2S works through bridge networking, keep the `a2s` waits; if
   not, either fix port publication (`-public 1` is not required for A2S, but
   Valheim's Steam relay init may be) or honestly downgrade the test contract
   to the generic surface like other migrated lanes.
4. **Done: config sync gap audit.** AGENTS.md requires
   `sync_server_config` + `config_sync_keys` for modules whose `set` values
   map to real game config. The repo now has
   `scripts/list_missing_config_sync_contracts.py` mirroring the static
   contract heuristic, and the current tree reports zero modules managing real
   server config without a declared config-sync contract.
5. **Steam auth-profile flow.** The provider-requirement contract in AGENTS.md
   anticipates mapping SteamCMD-auth-gated installs (the 47 ENABLED (AUTH)
   rows) through a shared auth-profile mechanism instead of per-module fail-fast
   messages. This is the single highest-leverage feature for converting AUTH
   rows into PASSED rows.

## 3. Support-State Backlog

1. **ENABLED (BYO) automation.** 41 modules fail fast pending operator-staged
   assets. For the subset where an authoritative direct download exists
   (GitHub releases, vendor archives), wire real installs and promote to
   PASSED. Each one is a self-contained PR: module install path + smoke +
   integration + tracker row + changelog.
2. **The 3 remaining DISABLED rows** (`abfserver`, `bobserver`, and legacy
   `counterstrikeglobaloffensive`). Re-verify each evidence note periodically;
   disabled rows rot fast in this repo's history.
3. **Done: tracker freshness automation.** CI now fails when
   `docs/TEST_STATUS.md` drifts from `enabled_*_servers.conf` or
   `disabled_servers.conf`, and it also rejects modules that appear in both
   enabled and disabled gate files at once.

## 4. Code Health

1. **Done: remove legacy `src/downloadermodules/steamcmd.py`.**
   The repo now uses `src/utils/steamcmd.py` exclusively for Steam app
   installation, so the dead parser-broken downloader module was deleted
   instead of preserved behind special lint and coverage exclusions.
2. **Done: repo-root clutter.** Legacy reference files now live under
   `docs/archive/`, `docs/reference/lgsm/`, or `scripts/legacy_*`, while
   one-off CI/smoke/test capture artifacts and the stray checked-in Warband
   archive were removed from repo root. Recurring generated log filenames are
   now ignored.
3. **Done: `changelog.txt` format split.** Historical stragglers were
   normalized to the current `- ` bullet format under date headings, matching
   `skills/changelog-discipline/SKILL.md`.
4. **Unit-test boilerplate.** A shared helper now exists at
   `tests/unit_tests/gamemodules/helpers.py`, and the actively edited
   Avorion, Beasts of Bermuda, Broken Arrow, Life is Feudal, Starbound, and
   Valheim coverage suites already import it instead of re-declaring local
   `DummyData` / `DummyServer` copies. Continue migrating touched files
   opportunistically so the duplication shrinks without forcing a giant
   one-shot sweep.
5. **Done: aggregate vs. per-module unit tests.** The duplicate aggregate
   files (`test_more_steam_dedicated_modules.py`,
   `test_steam_standalone_modules.py`) were removed after migrating their
   useful assertions into the affected per-module `*_cov.py` suites, so
   module-specific behaviour now has one test home instead of two.

## 5. Documentation

1. **Done: remove stale `future_plans`.** Its surviving ideas were already
   covered by the maintained roadmap themes here, so the duplicate file was
   dropped instead of leaving another stale planning surface behind.
2. **Done: README/docs/DEVELOPERS split.** The repo docs now lead with the
   Docker-manager quick start and the direct-host Docker-runtime path, while
   documenting host-process `screen` flows as the fallback path instead of the
   default. The user-facing runtime baseline is now called out as Ubuntu 24.04
   or newer Linux.
3. **Done: server guide status notes.** The support-tracked guides under
   `docs/servers/` now carry an explicit top-of-guide status note or a
   matching near-top support-status block aligned to the checked-in tracker
   state, including the Ubuntu 24.04 Linux baseline and the current
   process-versus-Docker validation shape where that distinction matters.

## 6. Future Feature Ideas

Larger, user-facing directions beyond the maintenance backlog. None of these
are started; each would need its own design pass against the AGENTS.md
contracts before implementation.

**Upstream scope policy.** AlphaGSM's job is the single-host management,
normalization, and machine-readable layer. Use this rule of thumb when
evaluating new feature work:

- **In scope (upstream):** machine-readable output, query/console protocols,
  lifecycle events, per-host policy (schedules, watchdogs, limits),
  install/update/export plumbing, packaging.
- **Out of scope (downstream/platform territory):** identity and accounts,
  permissions/ownership/audit, multi-host fleet orchestration, remote
  transports, and any internet-facing or hosted access surface. AlphaGSM
  stays a single-host, single-user tool by design; richer experiences should
  build *on top of* its JSON CLI output, not inside it.

1. **Steam auth profiles (the committed one, highest priority).** A shared
   credential-profile store for SteamCMD logins, surfaced through the
   existing `get_provider_requirements` contract, with `alphagsm <name> set
   steamprofile <profile>` style wiring. Unlocks ~47 ENABLED (AUTH) modules
   and is already anticipated by AGENTS.md.
2. **Scheduled operations.** First-class `update`/`backup`/`restart` schedules
   (cron-backed or an internal scheduler) per server, instead of operators
   hand-writing crontab entries around the CLI. Includes graceful-restart
   warnings broadcast through the existing `send_to_server` console path.
   Schedules should be CLI-native and inspectable (`info --json`) so external
   tools can drive them as the single source of truth.
3. **Auto-update on start / update checks.** Modules already know their Steam
   app id or release source; add an opt-in `set autoupdate true` that checks
   for a newer build during `prestart` and applies it before launch.
4. **Unified RCON / remote-console abstraction.** Many modules speak Source
   RCON, Minecraft RCON, or a bespoke TCP console. A shared `server.console`
   layer (like `server.runtime`) would give every module `command`,
   `broadcast`, `kick`, and player-list support, and make `send_to_server`
   protocol-aware instead of screen/stdin-only. High value: downstream tools
   should build on this instead of reimplementing per-game protocols.
5. **Player/state surface in `info`.** Extend `info --json` with player
   counts and names where the query protocol already returns them (A2S does),
   so dashboards can be built on top without extra probes. High value and
   cheap; machine-readable output is squarely in upstream scope.
6. **Webhook / Discord notifications.** Emit lifecycle events (started,
   stopped, crashed, update applied, backup completed) to a configurable
   webhook. Crash detection falls out of the runtime layer's exit-status
   handling. In scope as plain event *emission* (fire-and-forget POST);
   notification routing, digesting, or management UIs are downstream concerns.
7. **Crash watchdog / auto-restart.** Optional supervision: if the managed
   process or container exits non-zero, restart with backoff and notify. Both
   runtimes already know liveness; this is mostly policy plus state tracking.
   Pairs with item 6: upstream owns the restart *policy* and the lifecycle
   *events*; presentation of those events lives downstream.
8. **Resource limits and accounting.** Per-server CPU/memory limits — trivial
   to plumb for the Docker runtime (`--cpus`, `--memory`), cgroup-based for
   process mode — plus `info` reporting of current usage. The old
   `future_plans` idea of configurable launch arguments (e.g. Minecraft JVM
   memory) belongs here as module-level `set` keys validated by config sync.
9. **Server migration / export-import.** `alphagsm <name> export` producing a
   portable archive (datastore entry + world/saves + curated content
   manifest) and a matching `import`, enabling host moves and cloning. Pairs
   naturally with the backup system.
10. **Kubernetes / compose output.** Modules already produce a full container
    spec; add `alphagsm <name> spec --format compose|k8s` to emit a
    docker-compose service or a Pod manifest from `get_container_spec`, for
    users who want to run the result under their own orchestrator.
11. **Podman/rootless container support.** The runtime shells out to `docker`;
    abstract the binary and verify rootless Podman compatibility (port
    publication and mount semantics differ slightly).
12. **Curated content expansion.** Extend the curated manifest system to more
    ecosystems with authoritative release assets (per AGENTS.md scope:
    multiplayer server content only) — e.g. more Source addon families, Paper
    plugin sets, Valheim server-side mods via BepInEx — including a
    `mods update` path that re-pins manifest versions.
13. **Config templating.** The old `future_plans` "manage server.cfg" idea,
    generalized: per-module template files rendered from datastore values,
    superseding hand-edited config merges where modules currently rewrite
    files line-by-line.
14. **First-class packaging.** Publish to PyPI (the `pyproject.toml` exists)
    and ship the prebuilt binary from `scripts/build_binary.py` as a GitHub
    release asset per tag, so installs stop requiring a git clone.
15. **Interactive TUI.** A `alphagsm tui` dashboard (textual/urwid) showing
    all servers, status, ports, and recent log lines — low effort once the
    JSON info surface is complete, and a big quality-of-life win over running
    `info` per server.

## 7. Implementation Sketches for Section 6

Code-level plans for each feature, grounded in the current architecture.
Relevant existing surfaces:

- Command dispatch: `Server.default_commands` + `module.commands` in
  `src/server/server.py` (`get_commands()` ~L623, dispatch ~L754). New
  manager-level commands extend `default_commands`/`default_command_args`/
  `default_command_descriptions`; new module hooks follow the existing
  optional-hook pattern (`getattr(self.module, "hook", None)`).
- Datastore: per-server JSON via `JSONDataStore` in `src/server/data.py`,
  already supporting `set_secret_keys(...)` (separate 0600 secrets file).
- Runtime: `src/server/runtime.py` — `RUNTIME_FAMILY_DEFAULTS`,
  `RUNTIME_DATA_KEYS`, `build_container_spec`, `stop_mode`, and
  `send_to_server`.
- Cron: `Server.activate()`/`deactivate()` already manage user crontab
  entries via the `crontab` package (~L1881/L1919).
- Shared module builders: `src/utils/gamemodules/common.py`.

Every feature below also needs: unit tests under `tests/unit_tests/`,
integration coverage where lifecycle behaviour changes, `changelog.txt`,
`DEVELOPERS.md` (new hooks), and `docs/` user guidance, per AGENTS.md.

1. **Steam auth profiles.**
   - New `src/utils/steam_auth.py`: profile store at
     `~/.alphagsm/steam_profiles/<profile>.json` using `JSONDataStore` with
     `set_secret_keys({"password", "token"})`; never store plaintext beyond
     what SteamCMD itself needs — prefer relying on SteamCMD's own cached
     session, storing only the username and a "login validated" marker.
   - `alphagsm steamauth login <profile>` as a manager-level command in
     `src/core/main.py` (interactive `steamcmd +login <user>` passthrough so
     Steam Guard prompts reach the operator's terminal).
   - Extend `make_steamcmd_install_hook(...)` in `utils/gamemodules/common.py`
     to read `server.data.get("steamprofile")` and pass `+login <user>`
     instead of `+login anonymous`; add `steamprofile` to settable keys and
     to `get_provider_requirements` resolution (requirement satisfied when a
     valid profile is configured).
   - Docker note: SteamCMD session cache must be mounted into the
     `steamcmd-linux` container (extend `_steamcmd_sdk_mounts`).
   - Tests: unit tests for profile resolution and hook arg construction;
     CI cannot do real Steam Guard, so integration stays mocked.
2. **Scheduled operations.**
   - Reuse the existing crontab plumbing from `activate()`/`deactivate()`:
     add `server.data["schedules"]` (list of `{op, cron_expr, args}`) and a
     `schedule` default command (`add`/`remove`/`list`) that syncs entries
     tagged with an AlphaGSM comment marker into the user crontab, same as
     activate does today.
   - Graceful restarts: schedule `alphagsm <name> restart --warn 300`; the
     warn path loops over `runtime_module.send_to_server(...)` broadcasts.
   - Expose schedules in `info --json`.
3. **Auto-update on start.**
   - New optional module hook `check_update(server) -> bool` (SteamCMD
     modules get a shared implementation comparing
     `steamcmd +app_info_print` buildid against
     `server.data["installed_buildid"]`, recorded at install time by
     `make_steamcmd_install_hook`).
   - In `Server.start()`, before `prestart`: if
     `server.data.get("autoupdate")` and `check_update(...)`, call the
     existing update path. `set autoupdate true|false` joins settable keys.
4. **Unified console abstraction.**
   - New `src/server/console.py` mirroring `runtime.py`'s shape: a
     `ConsoleBackend` per protocol — `screen-stdin` (wraps current
     `send_to_server`), `source-rcon`, `minecraft-rcon`, `tcp-line`.
   - Modules declare `get_console_spec(server)` returning
     `{protocol, host, port, password_key}`; absent hook falls back to the
     current stdin path so nothing breaks.
   - Rewire the existing `send` default command and `do_stop` console paths
     through it. RCON passwords go through datastore secret keys.
   - Start with Source RCON (biggest module family), then Minecraft.
5. **Player info in `info --json`.**
   - The A2S query path already receives player counts in
     `A2S_INFO` responses; extend the query helper to also issue
     `A2S_PLAYER` and merge `{players: {count, max, names[]}}` into the JSON
     payload when the protocol supports it. Other protocols return `null`,
     never a guess. Schema is additive only.
6. **Webhook notifications.**
   - New `src/utils/events.py`: `emit(server, event, payload)` doing a
     fire-and-forget HTTP POST (stdlib `urllib`, short timeout, failures
     logged not raised) to `server.data.get("webhook_url")` or a global
     `[notifications] webhook_url` setting.
   - Call sites: start/stop/update/backup completion in `server.py`, crash
     detection from item 7. Event names are part of the public contract —
     document them in `DEVELOPERS.md`.
7. **Crash watchdog.**
   - Cheapest robust form on the existing architecture: a
     `alphagsm <name> watchdog-check` hidden command that verifies liveness
     (process: screen session; docker: `docker inspect` state) and restarts
     with backoff state kept in `server.data["watchdog"]`; scheduled every
     minute via the item-2 scheduler. Avoids inventing a daemon.
   - Emits `crashed`/`restarted` events through item 6.
8. **Resource limits.**
   - Docker: add `cpus`/`memory` to `RUNTIME_DATA_KEYS` and thread them into
     the `docker run` argv in `ContainerRuntime.start()`.
   - Process mode: out of scope initially (document as Docker-only); cgroup
     v2 wiring can come later.
   - Usage reporting: `docker stats --no-stream` (or `/proc/<pid>` for
     process mode) merged into `info --json`.
9. **Export / import.**
   - `alphagsm <name> export [file.tar.gz]`: tar of the datastore JSON
     (secrets excluded by default), the install dir's *user data* subset —
     modules declare it via a new optional `get_user_data_paths(server)`
     hook, falling back to whole-dir — plus a manifest with module name,
     version, and AlphaGSM version.
   - `alphagsm import file.tar.gz <newname>`: create + restore datastore
     keys (re-running port claims through `port_manager` rather than
     trusting exported ports), then `setup` to re-download binaries, then
     unpack user data. Reuses the backup code paths where possible.
10. **Compose / k8s emission.**
    - `alphagsm <name> spec --format compose|k8s|json`: pure read-only
      serialization of `build_container_spec(...)` output. Compose first
      (trivial mapping: image, command, volumes, ports, environment); k8s
      Pod manifest later. No new state; ~1 new module
      (`src/server/spec_export.py`) plus a default command.
11. **Podman support.**
    - Replace hardcoded `docker` argv head in `runtime.py` with a
      `container_engine()` helper reading `[runtime] engine` setting
      (default `docker`, auto-detect fallback to `podman` when docker is
      absent). Audit for docker-only flags (`--network bridge` semantics,
      `docker stats`) and gate them. Add a CI lane variant only if a podman
      runner is practical; otherwise unit-test the argv construction.
12. **Curated content expansion.**
    - No new architecture: per-module `curated_*.json` manifests beside the
      module (per AGENTS.md), shared install path fixes at the root cause,
      dependency-aware apply. Add `mods update` to re-pin manifest versions:
      a script comparing manifest URLs/versions against upstream release
      APIs, run manually, emitting a diff for review.
13. **Config templating.**
    - Extend the existing `sync_server_config` contract rather than invent a
      new one: shared helper `render_config_template(server, template_path,
      dest_path)` in `utils/gamemodules/common.py` using
      `string.Template`-style substitution from datastore keys; modules opt
      in per file. Keeps `config_sync_keys` as the declared sync surface.
14. **Packaging.**
    - PyPI: `pyproject.toml` already exists — add entry point
      `alphagsm = core.main:main`, validate `pip install .` in a CI job, and
      publish on tag via a `pypa/gh-action-pypi-publish` workflow.
    - Binary: extend the existing release workflow to upload the
      `scripts/build_binary.py` artifact per tag (the 3-OS binary smoke jobs
      already prove it builds).
15. **TUI.**
    - Build strictly on `info --json` and the list command — the TUI is a
      consumer, not a new API. `src/core/tui.py` behind an optional
      `textual` dependency (`pip install alphagsm[tui]`), registered as the
      `tui` manager command. Defer until items 2 and 5 stabilize the JSON
      schema.

**Suggested implementation order** (dependencies first): 5 → 6 → 2 → 7
(events/scheduler stack), 1 (auth profiles, independent), 8/10/11 (runtime
layer, independent of each other), 3 (needs install buildid recording),
4 (console layer), 9 (export), 13/12 (config/content), 14 → 15 (packaging,
then TUI on the stabilized JSON surface).

## 8. Security Implications and Mitigations

Security requirements for the Section 6/7 features, especially anything that
touches credentials. Treat these as hard constraints, not suggestions.

### Steam credentials and auth profiles (items 1, 3)

- **Never store Steam passwords.** The design in Section 7.1 is deliberate:
  run `steamcmd +login <user>` interactively once so SteamCMD caches its own
  session ticket; AlphaGSM stores only the username and a "validated"
  marker. AlphaGSM must not implement its own password prompt, must not
  accept passwords as CLI arguments (they leak via shell history and
  `/proc/<pid>/cmdline`), and must not write passwords to the datastore,
  logs, or environment variables.
- **Protect the SteamCMD session cache.** The cached ticket
  (`~/Steam/config/`, `config.vdf`) is bearer material — possession grants
  the account's install entitlements. The profile store and any session
  cache directory AlphaGSM manages must be created `0700` (dirs) / `0600`
  (files), owned by the invoking user, with permissions verified (and an
  explicit warning) on every load, mirroring how SSH treats key files.
- **Docker mount discipline.** When mounting the session cache into
  `steamcmd-linux` containers, mount it read-only wherever the operation
  allows, mount only the minimal subtree (not the whole Steam dir), and
  never bake credentials into images or pass them via `docker run -e`
  (visible in `docker inspect`). Files only.
- **Steam Guard.** Interactive login is the only supported 2FA path. Do not
  add flags that accept Guard codes non-interactively from scripts; that
  trains users to pipe secrets through automation.
- **Logout/rotation path.** Ship `steamauth logout <profile>` from day one:
  it must remove the cached session and the profile entry. Document that
  revoking access requires deauthorizing the machine in Steam, not just
  deleting local files.

### Tokens and per-module secrets (provider-token modules, RCON, webhooks)

- **Single mechanism.** All secret-bearing keys (provider tokens, RCON
  passwords, webhook URLs containing embedded tokens) must go through the
  existing `JSONDataStore.set_secret_keys(...)` path — a separate `0600`
  secrets file beside the main datastore — never the main JSON, which users
  routinely paste into issues. Each module/feature declares its secret keys;
  a static unit test should assert that known-sensitive key names
  (`*token*`, `*password*`, `*secret*`, `webhook_url`) are registered as
  secret wherever a module defines them.
- **Redaction at the boundaries.** `info`, `info --json`, `set` echo output,
  error messages, and the Section 7.6 event payloads must mask secret values
  (`"***"`), and the export archive (7.9) must exclude the secrets file by
  default — re-entering credentials on the destination host is the safe
  default; an explicit `--include-secrets` flag may exist but must warn.
- **No secrets in argv or env.** When a game server needs a token at launch,
  prefer writing it into the game's own config file (`0600`) over command
  line arguments or container env vars, both of which are world-inspectable
  (`ps`, `docker inspect`). Where a game only accepts an env var, document
  the exposure in that server's guide.

### Feature-specific notes

- **Webhooks (7.6):** outbound only, HTTPS enforced by default (allow
  `http://` only with an explicit opt-in setting), no redirect following,
  short timeout, and payloads limited to lifecycle metadata — never config
  dumps or paths. Webhook URLs are secrets (Discord URLs embed the token).
- **Console/RCON layer (7.4):** RCON is plaintext on the wire; default the
  console spec host to `127.0.0.1`/container-local and document that
  exposing an RCON port publicly requires the game-side allowlist/strong
  password. Generate strong random RCON passwords at install time instead of
  defaulting to anything guessable; store via secret keys.
- **Export/import (7.9):** validate archives on import — reject absolute
  paths and `..` traversal in tar members (use a safe-extract helper, not
  bare `tarfile.extractall`), re-claim ports through `port_manager`, and
  treat the manifest's module name as untrusted input (must match an
  installed module, no dynamic import of arbitrary names).
- **Scheduler/watchdog (7.2, 7.7):** crontab entries run arbitrary commands
  as the user; the `schedule add` path must only accept whitelisted AlphaGSM
  operations (`update`, `backup`, `restart`, `watchdog-check`), never a raw
  command string.
- **Spec emission (7.10):** emitted compose/k8s files inherit any env-based
  secrets in the container spec; scrub or placeholder secret values in the
  output and say so in a comment header.
- **Curated content (7.12):** keep the existing posture — immutable,
  authoritative release URLs only; record and verify a SHA-256 per manifest
  entry at download time so a compromised upstream re-tag cannot silently
  change payloads.

## 9. Suggested Pick-Up Order for a Future Agent

1. Check the latest `release_v1` CI run; fix whatever the newest red gate is
   (fast gates first, then `slow-*` lanes, then batches).
2. Resolve the btserver/valheim Docker A2S question (Section 2.3) and align
   smoke runners (Section 1.6) — this closes out the in-flight migration.
3. Deduplicate the runtime-image resolvers (Section 1.1) and the executable
   resolver (Section 2.1) while the patterns are fresh.
4. Then pick either: more process→Docker lane migrations (Section 1.2) or
   BYO/AUTH promotions (Section 3) depending on appetite for long CI cycles.

Keep every change scoped: one lane/module per commit, tracker + guide +
changelog updated in the same PR, and never leave a server in an ambiguous
"investigated" state.
