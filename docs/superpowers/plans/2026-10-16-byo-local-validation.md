# All 42 BYO Helpers: Sequential Local Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for the campaign and the repository operations skills for each selected server. For code fixes, use superpowers:test-driven-development and requesting-code-review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exercise all 42 file-based BYO helpers individually on the SSD, establish what each can acquire/check, repair evidenced defects, and verify real server readiness where prerequisites permit.

**Architecture:** One active row and one game server at a time. Repair the shared authenticated-session prerequisite first, then test six SteamCMD helpers, three managed local-import helpers, and 33 manual-distribution helpers. Keep acquisition, declared-file validation, process readiness, protocol readiness, and Docker validation as separate results.

**Tech Stack:** AlphaGSM CLI from the existing worktree, private Linux SteamCMD profile, Python/pytest, native Linux and declared runtime families, isolated SSD game directories.

---

## Confirmed scope and current state

- The user selected all 42 helpers, starting with the six SteamCMD paths, and selected Quake III Arena first.
- Code: `/home/cosmosquark/.codex/worktrees/byo-file-helpers/AlphaGSM`, branch `codex/byo-file-helpers`, original reviewed baseline `1bb6c646`; cache fix `0da848f3`.
- Bulk data/cache/staging: `/media/cosmosquark/SSD/sector_alpha/github/AlphaGSM/.local-tests/byo-file-helpers` (about 470 GB free at preparation).
- CLI wrapper: that SSD directory's `run`. It explicitly selects this branch, isolated config, temporary directory, logs and unique session prefix.
- Steam profile: `owned`, under `/home/cosmosquark/.alphagsm-private/steam-auth/owned/`. Authentication/runtime cache stays on the private Linux filesystem; SSD NTFS permissions do not meet the profile's trusted-parent policy.
- The existing interactive session successfully acquired owned Quake III files. This verifies access to AppID 2200 for this test; ownership of other queued apps remains unverified.
- Fixed shared defect in `0da848f3`: recognize `home/Steam/config/config.vdf` as well as the legacy runtime cache, preserving private-path checks. The existing `owned` session reports present and subsequently acquired AppID 2200 successfully.
- `byossdq3` completed authenticated setup, native Quake UDP query/info and verified shutdown on the SSD. Nine owned PK3 files passed ownership hashes; repeat setup skipped SteamCMD. Docker remains NOT_RUN. Evidence: SSD `results/q3server/2026-10-16-auth-first.json`.
- The approved auth-first setup implementation precedes the selected Q3 attempt. No background loop or other game acquisition is scheduled.

The JSON file beside this plan is the machine-readable queue. It contains no account identifier or secret material. Preserve exact module IDs, tags, order and per-row evidence. Source instructions are checked-in metadata, not proof that a historical URL currently works; verify upstream availability at each row before downloading.

The three non-file BYO prerequisites (Astroneer endpoint, Quake Live entitlement, Life is Feudal database) are outside this 42-file-helper campaign.

## Operating rules

1. Start with the first unresolved eligible row. Never run two acquisitions, setups or game servers concurrently.
2. Fix shared defects before advancing any affected row. A game-specific missing entitlement/archive/export can be recorded as blocked, then the next independent row can proceed after shutdown and cleanup.
3. A timeout is a failure to diagnose, not a passing result or a permanent skip. Retry only after identifying and correcting a cause; avoid identical blind retries.
4. Use AlphaGSM commands for lifecycle changes. Do not invoke a game executable directly to manufacture success.
5. Never read/copy raw credential-cache contents, save passwords/Guard codes, use anonymous fallback for an authenticated source, or place auth profiles in SSD evidence. Provider secrets and secret-bearing exports also require private storage; stop that row if its current layout cannot preserve this.
6. Do not infer complete distribution integrity from `sentinel-only` checks. Keep automatic import disabled for those 33 recipes unless a separately tested, authoritative layout justifies changing it.
7. Temporary validation ends stopped. Verify the owned process/container and all claimed listeners are gone before starting the next row.
8. Leave the original checkout's unrelated Reclaimer changes untouched. Code fixes go into the managed feature worktree; local generated game data stays ignored on the SSD.

## Per-game completion rule: reusable install and full server content

The user clarified that each game must leave reproducible setup code, not only
files staged manually for a local test. Install enough to run the dedicated
server with as much compatible content as its declared legitimate source
provides. Keep maps, their supporting assets, packages, game scripts and required
runtime libraries. Minimum file sentinels do not define the entire install.
Remove disposable full-client staging and omit known unrelated client engine
components. Preserve content archives whole and never prune untracked operator
files as an install cleanup shortcut.

Before closing a row, check in its acquisition/install/import selection plus
regressions proving complete server content is retained, document the source
and runnable layout, and validate through AlphaGSM commands. If the complete
layout or required input is unavailable, record the specific blocker and keep
that row incomplete. Never count an ad hoc manual copy or sentinel-only result
as a reusable complete installation.

Q3 retains nine base/patch PK3s containing 36 distinct BSP maps. Its dedicated
engine selection now omits 11 loose client components and passed a repeated
native lifecycle/shutdown check; other games will get their own
source-specific selection when reached, without applying Q3 exclusions globally.

## Task 0: Repair and verify isolated Steam cache discovery

**Modify:** `src/utils/steam_auth.py`, `tests/unit_tests/utils/test_steam_auth.py`, `changelog.txt`, `docs/steamcmd-auth.md`.

- [x] Add a regression to the existing auth test file. It uses synthetic cache contents only:

```python
def test_session_cache_under_isolated_steam_home(auth):
    profile = session(auth)
    cache = profile / 'home/Steam/config/config.vdf'
    cache.parent.mkdir(parents=True)
    (profile / 'runtime/config/config.vdf').replace(cache)
    assert auth.status('owned')['local_session'] is True
    with auth.download_session('owned') as (executable, username, env, lock_fd):
        assert executable == profile / 'runtime/steamcmd.sh'
        assert username == 'account_name'
        assert env['HOME'] == str(profile / 'home')
        assert lock_fd >= 0
```

- [x] Run it before fixing production code; expected failure is local-session missing because the legacy cache path is absent.
- [x] Replace the single cache-location predicate in `_session_username` with the two known profile-contained locations, preserving every other metadata/executable/ownership/link check:

```python
caches = (profile / 'home/Steam/config/config.vdf',
          profile / 'runtime/config/config.vdf')
if not any(cache.is_file() and cache.stat().st_size for cache in caches):
    raise ValueError
```

- [x] Add login-path coverage where the fake SteamCMD process writes the cache under its provided isolated HOME. Retain the old runtime-cache regression, missing-cache rejection, lock/cancellation tests, and unsafe-link/owner tests. Do not recursively search arbitrary locations for cache files.
- [x] Run `tests/unit_tests/utils/test_steam_auth.py` and `tests/unit_tests/core/test_steam_auth.py` with `/tmp/alphagsm-agent-venv/bin/python`, then changed-file pylint. Host filesystem execution is needed because the sandbox remaps root ownership. Read the changelog skill before updating release notes.
- [x] Review and commit the focused fix. Update the auth guide to explain both supported isolated layouts without exposing cache contents.
- [x] Run the SSD wrapper's `steam-auth status owned`. Expected: local session present using the existing cache; this still does not prove Valve access. Ask for direct terminal login again only if the subsequent real download proves the session must be refreshed.

## Queue

Rows 1–6 exercise authenticated acquisition. Rows 7–9 use managed imports from operator-supplied files or exports. Rows 10–42 currently permit inspection/guidance only and need complete manual distributions before a lifecycle attempt.

| # | Module / test tag | File prerequisite / acquisition focus | Initial state |
| --- | --- | --- | --- |
| 1 | `q3server` / `byossdq3` | baseq3/pak0.pk3 — Steam 2200 (Windows owned data) | COMPLETE_PROCESS_DOCKER_NOT_RUN |
| 2 | `rtcwserver` / `byossdrtcw` | 14 declared multiplayer PK3 files; separate compatible patch data — Steam 9010 (Windows owned data) | NOT_STARTED |
| 3 | `codserver` / `byossdcod` | main/*.pk3 — Steam 2620 (Windows owned data) | NOT_STARTED |
| 4 | `coduoserver` / `byossdcoduo` | main/pak0.pk3 OR main/default_mp.cfg — Steam 2620 (Windows owned data) | NOT_STARTED |
| 5 | `cod2server` / `byossdcod2` | main/localized_*.iwd OR main/default_localize_mp.cfg; main/*.iwd — Steam 2630 (Windows owned data) | NOT_STARTED |
| 6 | `cod4server` / `byossdcod4` | fileSysCheck.cfg; main/*.iwd; main/localized_*.iwd; zone/*.ff OR zone/*/*.ff — Steam 7940 (Windows owned data) | NOT_STARTED |
| 7 | `etlegacyserver` / `byossdetlegacy` | etmain/pak0.pk3 — managed local import | NOT_STARTED |
| 8 | `ets2server` / `byossdets2` | {configdir}/server_packages.sii; {configdir}/server_packages.dat — managed local import | NOT_STARTED |
| 9 | `atsserver` / `byossdats` | {configdir}/server_packages.sii; {configdir}/server_packages.dat — managed local import | NOT_STARTED |
| 10 | `ahlserver` / `byossdahl` | action/maps/ahl_hydro.bsp — manual complete distribution | NOT_STARTED |
| 11 | `alienarenaserver` / `byossdalienarena` | {exe_name}; data1 — manual complete distribution | NOT_STARTED |
| 12 | `aloftserver` / `byossdaloft` | {exe_name} — manual complete distribution | NOT_STARTED |
| 13 | `atlasserver` / `byossdatlas` | ShooterGame/ServerGrid.json; ShooterGame/ServerGrid.ServerOnly.json; ShooterGame/ServerGrid — manual complete distribution | NOT_STARTED |
| 14 | `bbserver` / `byossdbb` | brainbread/maps/bb_chp4_slaywatch.bsp — manual complete distribution | NOT_STARTED |
| 15 | `bf1942server` / `byossdbf1942` | {exe_name} — manual complete distribution | NOT_STARTED |
| 16 | `bfvserver` / `byossdbfv` | {exe_name} — manual complete distribution | NOT_STARTED |
| 17 | `dstserver` / `byossddst` | {confdir}/{cluster}/cluster_token.txt; {confdir}/{cluster}/cluster.ini; {confdir}/{cluster}/{shard}/server.ini — manual complete distribution | NOT_STARTED |
| 18 | `foundryserver` / `byossdfoundry` | {exe_name} — manual complete distribution | NOT_STARTED |
| 19 | `goldeneyesourceserver` / `byossdgoldeneyesource` | {exe_name}; gesource/gameinfo.txt; gesource/maps/*.bsp — manual complete distribution | NOT_STARTED |
| 20 | `gravserver` / `byossdgrav` | {exe_name} — manual complete distribution | NOT_STARTED |
| 21 | `hogwarpserver` / `byossdhogwarp` | {exe_name} — manual complete distribution | NOT_STARTED |
| 22 | `identityserver` / `byossdidentity` | {exe_name} — manual complete distribution | NOT_STARTED |
| 23 | `jk2server` / `byossdjk2` | {exe_name}; base/assets0.pk3; base/assets1.pk3 — manual complete distribution | NOT_STARTED |
| 24 | `minecraft.custom` / `byossdminecraftcustom` | {exe_name} — manual complete distribution | NOT_STARTED |
| 25 | `minecraft.tekkit` / `byossdminecrafttekkit` | {exe_name}; mods — manual complete distribution | NOT_STARTED |
| 26 | `mohaaserver` / `byossdmohaa` | {exe_name}; main/*.pk3 — manual complete distribution | NOT_STARTED |
| 27 | `mxbikesserver` / `byossdmxbikes` | {exe_name} — manual complete distribution | NOT_STARTED |
| 28 | `ndserver` / `byossdnd` | nucleardawn/maps/hydro.bsp — manual complete distribution | NOT_STARTED |
| 29 | `nsserver` / `byossdns` | ns/maps/ns_hera.bsp — manual complete distribution | NOT_STARTED |
| 30 | `q4server` / `byossdq4` | {exe_name}; q4base/*.pk4 — manual complete distribution | NOT_STARTED |
| 31 | `sampserver` / `byossdsamp` | {exe_name}; gamemodes/*.amx — manual complete distribution | NOT_STARTED |
| 32 | `sfcserver` / `byossdsfc` | sfclassic/maps/sf_astrodome.bsp — manual complete distribution | NOT_STARTED |
| 33 | `skyrimtogetherrebornserver` / `byossdskyrimtogetherreborn` | {exe_name} — manual complete distribution | NOT_STARTED |
| 34 | `sof2server` / `byossdsof2` | {exe_name}; base/*.pk3 — manual complete distribution | NOT_STARTED |
| 35 | `ss14server` / `byossdss14` | {exe_name} — manual complete distribution | NOT_STARTED |
| 36 | `starbound` / `byossdstarbound` | {exe_name}; assets/packed.pak — manual complete distribution | NOT_STARTED |
| 37 | `stormworksserver` / `byossdstormworks` | {exe_name}; data — manual complete distribution | NOT_STARTED |
| 38 | `subnauticaserver` / `byossdsubnautica` | Subnautica_Data/Managed/Assembly-CSharp.dll; Subnautica_Data — manual complete distribution | NOT_STARTED |
| 39 | `tsserver` / `byossdts` | ts/maps/ts_neobaroque.bsp — manual complete distribution | NOT_STARTED |
| 40 | `ut3server` / `byossdut3` | {exe_name}; Engine; UTGame — manual complete distribution | NOT_STARTED |
| 41 | `vsserver` / `byossdvs` | vs/maps/vs_frost.bsp — manual complete distribution | NOT_STARTED |
| 42 | `zmrserver` / `byossdzmr` | zombie_master_reborn/maps/zm_docksofthedead.bsp — manual complete distribution | NOT_STARTED |

## Task 1: Validate each SteamCMD row, beginning with Quake III

The explicit order is Q3 → RTCW → CoD → United Offensive → CoD 2 → CoD 4. Check entitlement for the selected source by attempting the authenticated source exactly once after auth readiness; do not assume the account owns every title. The United Offensive helper downloads original CoD base content from app 2620; the expansion's `uo/` distribution remains a separate prerequisite. Passing that base-file helper alone is not a complete UO server pass.

For each row, complete the following checklist and update its JSON record immediately:

- [ ] Inspect `assets requirements --json`, the exact module guide, install/prestart code and runtime requirements. Save the declared recipe, commit, source app/platform, selected settings and disk baseline as credential-free evidence.
- [ ] Reuse only the campaign's matching tag; create it if absent. Inspect `help setup` and `set --list` before constructing setup commands. Set only this row's SSD installation directory. Select free values for the entire port-claim set; do not assume a default port is free or change global backends.
- [ ] Verify host libraries, executable architecture and runtime availability before setup. Steam-owned Windows data may be compatible asset input without being a Linux server binary.
- [ ] Check disk headroom for the full source app, selected imported files, engine archive/cache and a safety margin. Abort before download if the estimate is unknown or insufficient; use authoritative depot/install-size information when needed. Recheck actual free space after acquisition. Check private-home free space too before installing Steam runtimes, Wine/Proton prefixes or other Linux-filesystem-only state; never bypass credential permissions or move an incompatible prefix onto NTFS to make space.
- [ ] Prefer `setup -n ... --auth-profile owned` with no raw credential output capture. This configures the destination, acquires missing owned files, and installs the engine. Use standalone `assets fetch steam-owned --auth-profile owned` only for file-only diagnosis/refresh. Confirm the source-specific SteamCMD success result, selected canonical filenames, ownership manifest, and removal of temporary `.alphagsm-byo-*` staging. Record failed downloads as failed/blocked with the sanitized cause.
- [ ] Run `assets check --json`; require the declared files. Compare selected file hashes and the ownership manifest; confirm unrelated client files and profile contents were not published. Use local managed export/import for idempotency checks rather than downloading the full app repeatedly.
- [ ] Confirm the preferred setup finished and remembered only the profile name. Later setup reuses it without another download when declared files remain valid. Run file checks again to catch engine archive overwrites or layout drift. An explicit `--steam-dir PATH` or `--assets PATH` is the local-source alternative.
- [ ] Run doctor; distinguish missing external prerequisites from actual implementation failures. Start only after the selected configuration and installed executable are understood.
- [ ] Start through AlphaGSM, wait with a finite game-appropriate deadline, then require `status`, `query`, `info`, and `info --json` to describe the actual server and configured map. See the protocol audit below.
- [ ] In a `finally` cleanup path, stop the selected tag and prove process/container termination plus listener closure. A failed query/start also requires cleanup before advancing.
- [ ] Where Docker capability is part of a support-enablement claim, repeat lifecycle validation with the declared branch-local runtime image after native validation; record image/commit/ports and shutdown. Otherwise leave Docker explicitly NOT_RUN, without claiming full runtime parity.
- [ ] Record results, evidence paths, blocker/fix, disk use and final stopped state. Update applicable public tracker/guide immediately after a real lifecycle run; preserve AUTH/BYO prerequisite classification.

### Exact first-row acquisition commands

These run only after Task 0 and after the plan enters execution. `byossdq3` already exists and its SSD directory is configured:

```bash
RUN=/media/cosmosquark/SSD/sector_alpha/github/AlphaGSM/.local-tests/byo-file-helpers/run
"$RUN" steam-auth status owned
"$RUN" byossdq3 assets requirements --json
"$RUN" byossdq3 help setup
# After confirming the actual port/directory options and free claims:
"$RUN" byossdq3 setup -n --auth-profile owned
"$RUN" byossdq3 assets check --json
```

Issue dependent commands sequentially and inspect each result. Resolve a free port and the actual supported setup arguments before invoking setup. An acquisition failure must prevent engine installation and lifecycle continuation. Once configured, the first row's lifecycle commands are:

```bash
"$RUN" byossdq3 doctor --json
"$RUN" byossdq3 start
"$RUN" byossdq3 status
"$RUN" byossdq3 query
"$RUN" byossdq3 info
"$RUN" byossdq3 info --json
"$RUN" byossdq3 stop
"$RUN" byossdq3 status
```

Use try/finally around the started interval during execution. Q3 requires real Quake UDP readiness and JSON `protocol: quake`; inspect all claimed sockets and the owned process afterward. A TCP-close check alone does not establish UDP shutdown.

### Protocol audit before any lifecycle pass

`tests/integration_tests/test_q3server.py` already expects Quake UDP. In the current tree, RTCW's integration test expects A2S, while CoD-family query/info hooks and integration tests expect TCP. Those expectations have not been validated in this campaign and must not be accepted as proof that the game actually speaks them.

At the selected row, establish the real protocol from the installed engine and authoritative upstream documentation, and observe a valid native response. If existing hooks/tests disagree, correct the shared/module protocol wiring, add a regression, retain Docker wrappers, and update smoke/integration expectations together. Do not broaden assertions to several protocols, accept a TCP fallback as game readiness, or count a log marker as query success.

## Task 2: Validate the three managed manual-import helpers

- [ ] **Enemy Territory Legacy:** obtain original ET `etmain/pak0.pk3` from the declared legitimate source. Inspect/include applicable patch PK3s, then import/export/check and run the matching engine lifecycle. The engine download alone does not supply original data.
- [ ] **ETS2:** request the two genuine `export_server_packages` outputs from the operator's owned client and intended map/mod set. Steam login cannot generate these files. Test relative-home managed import and export; test absolute-home inspection and the expected manual-only mutation guard without changing the supplied originals.
- [ ] **ATS:** perform its own client export, import/export/check and relative/absolute-home tests. Do not substitute ETS2 exports.
- [ ] For every row with available data, perform the same setup/readiness/query/info/stop and evidence procedure as Task 1. Missing client exports are a concrete BLOCKED_ASSETS result, not a helper or lifecycle pass.

## Task 3: Iterate the 33 manual-distribution rows

Process the exact rows 10–42 in queue order. Their full declared requirements, original source instructions and guide paths are preserved in the JSON queue; use those records to resolve the specific operator prerequisite before downloading.

For each row:

- [ ] Inspect requirements before setup. Resolve configured path placeholders with actual settings. Record the source, release/version, platform, executable layout, complete companion-data requirements, and license/provider prerequisite.
- [ ] Verify upstream availability and download provenance. Prefer official/versioned releases. If no valid artifact exists, record the exact failed source or missing input; do not invent a URL or rename a Windows executable to look native.
- [ ] Request only the row's missing owned files/export/service prerequisite when reached; continue independent inspection of later rows when that external input is unavailable. Secret-bearing DST tokens and ATLAS ServerOnly configuration stay private and out of exports/evidence.
- [ ] Keep automatic fetch/import disabled for `managed_import: false`. Confirm the expected manual-staging explanation and read-only file checks. A matching executable/map sentinel is only partial file evidence.
- [ ] Stage a complete legitimate distribution only into that row's disposable SSD game directory, with required private configuration/runtime state on an appropriate protected Linux filesystem. Keep supplied source trees immutable. Wine/Proton prefixes must use a filesystem that supports their required Unix semantics; do not silently place an incompatible prefix on NTFS.
- [ ] Perform the same bounded AlphaGSM lifecycle and shutdown verification when prerequisites permit. Record unsupported platform, missing artifact, config/export, provider or runtime blockers precisely; do not convert them to PASSED.
- [ ] If an exact install layout becomes understood, implement managed import in a separate reviewed change with source evidence, selection/ownership/rollback tests, docs and changelog. A manual helper does not become managed merely because one supplied archive worked once.

Rows with known platform/distribution uncertainty include Aloft, FOUNDRY, GRAV, HogWarp, MX Bikes, Skyrim Together and Stormworks. Source/GoldSrc mod rows require complete mod resources and real native query readiness; do not accept the map sentinel or hibernation alone. Minecraft custom/Tekkit require exact project/version and EULA handling. Subnautica requires the selected Nitrox-compatible original-game build, not arbitrary assemblies.

## Task 4: Evidence, failure handling, storage and closure

- [ ] Create a timestamped result record per module under the SSD test root's `results/`. Record commit, module/tag, source app or archive identity/checksum, source and selected byte counts, return codes, file-check result, native protocol result, Docker result, final stopped state, and sanitized blocker/fix.
- [ ] Use result fields independently: acquisition PASSED does not imply file-validation PASSED; file-validation PASSED does not imply lifecycle PASSED. Keep `sentinel-only` explicitly visible even when its limited checks pass.
- [ ] On a shared auth/importer/runtime defect, pause affected rows, write a synthetic failing regression, make the smallest fix, run focused tests and lint, review, then retry the current row. Do not change queue order to conceal a failure.
- [ ] On unavailable ownership/export/artifact/runtime input, mark the row BLOCKED with a specific next action. After proving it stopped, proceed to the next independent eligible row. Report partial progress honestly.
- [ ] Preserve small redacted evidence and selected hashes. After recording a row and proving shutdown, remove only campaign-created scratch/staging/game copies when needed for the next row's disk budget; never delete operator-provided originals, the private profile or unrelated servers. Retain metadata and results so completed or blocked work is not rediscovered.
- [ ] Recheck SSD free space before every row. Only the current row may hold active full-app staging. Account for both downloader cache and retained installed copies; shared private Steam runtime remains outside the SSD game-data budget.
- [ ] Update `docs/TEST_STATUS.md`, the matching server guide and any affected support tracker immediately after actual lifecycle results. Legitimate owned-file success remains ENABLED (BYO); authenticated prerequisites remain AUTH where appropriate. Local private-session success is not self-provisioning CI evidence.
- [ ] For each code-fix batch, run focused regressions, `make test` and `make lint` using the verified environment; lint must be 10.00/10. Keep CI credential integration deferred as requested. Docker parity claims require their separate real evidence.
- [ ] Finish with a 42-row report: fully validated, files-only validated, partial/sentinel-only, failed, and blocked; list concrete remaining input for every unfinished row. Every attempted game must finish stopped.

## Execution boundary

This plan does not execute all 42 automatically. The shared cache-path fix is complete. The auth-first changes passed full tests/review and the selected Q3 process row is complete. RTCW is next in the queue; no other game acquisition has started. Reuse the existing login cache; only ask for a local interactive login if Valve access later requires it. Passwords and Guard codes are never requested in chat.
