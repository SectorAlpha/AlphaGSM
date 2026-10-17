# BYO helpers: agent handoff

Updated 2026-10-16 (Europe/London). This is a local repository handoff, not a completed all-games validation report. Raw authentication material is intentionally absent.

## User decisions and scope

- Build reusable, game-specific BYO helpers: each knows the files it needs and legitimate sources. Leave checked-in acquisition/install/import code, not just an ad hoc local installation.
- Prefer authenticated SteamCMD acquisition for declared supported Steam sources. Offer an explicit existing Steam-directory import alternative; preserve existing local directory/archive import.
- Remember the selected auth **profile name** per server. Never store passwords or session tokens in game settings.
- The installed result should be a runnable dedicated server with the fullest compatible content available from its declared source: maps, supporting assets, packages, scripts and runtime libraries. Minimum readiness sentinels do not define the entire payload. Keep content archives intact; omit known unrelated client binaries/renderers; remove disposable full-app staging.
- Validate all 42 file-based BYO helpers one game at a time, beginning with the six SteamCMD recipes. The user selected Quake III Arena first; it is complete for authenticated acquisition and native process validation. RTCW is next. The other 41 games have not been downloaded or tested in this campaign.
- For every game, test the actual configured game/query endpoint with its native TCP/UDP protocol, running `status`, `query`, `info`, and `info --json`. Verify returned server properties. A process, open socket, log marker, generic TCP fallback or file check alone is insufficient.
- Fix the game module or shared helper when those checks expose defects; check in a regression and rerun the real lifecycle before closing that row. Preserve config-sync, port-claim and explicit Docker runtime contracts.
- End temporary tests stopped, proving process/container termination and claimed listener release. Record probe scope; local success does not prove external reachability or Docker parity.
- Authenticated CI integration is deferred. Credential-free unit tests remain required. Existing user authorization covers local sequential SSD testing; no need to ask again for the same scope. A fresh interactive Steam login is needed only if the cached session stops working.
- No background job, recurring automation, concurrent game acquisition, push, merge or PR was requested or created.

## Exact execution locations

| Purpose | Location |
| --- | --- |
| Implementation worktree | `/home/cosmosquark/.codex/worktrees/byo-file-helpers/AlphaGSM` |
| Feature branch | `codex/byo-file-helpers` |
| Latest behavior implementation | `a1e2aebb` (installer behavior at `49daf65c`, auth-first setup at `c635d700`) |
| Workflow/docs commit | `da219845` |
| Latest per-game query/status policy commit | `278bd5bd` |
| Original checkout | `/media/cosmosquark/SSD/sector_alpha/github/AlphaGSM` |
| SSD test root | `/media/cosmosquark/SSD/sector_alpha/github/AlphaGSM/.local-tests/byo-file-helpers` |
| Test CLI wrapper | SSD test root + `/run` |
| Verified Python | `/tmp/alphagsm-agent-venv/bin/python` |
| Private AlphaGSM/auth root | `/home/cosmosquark/.alphagsm-private` |

**Do not edit/reset the original checkout's unrelated Reclaimer work.** Its working tree is dirty with unrelated tracked and untracked changes, including its own asset helpers. Source changes for this campaign belong in the managed worktree. Only the ignored `.local-tests` scratch directory in the SSD checkout was changed by this campaign.

Read this worktree's `AGENTS.md` and relevant repository skills. It has already been created/attached; reuse it. With the current sandbox, writes to the managed worktree and private-home auth operations may need `exec_command` with `sandbox_permissions: require_escalated`. That is a filesystem constraint, not a reason to move auth onto the SSD.

## Auth details: use the existing private profile

- Profile name: **`owned`**.
- Private profile directory: `/home/cosmosquark/.alphagsm-private/steam-auth/owned/`.
- The user completed an interactive SteamCMD login. This session successfully acquired Quake III AppID **2200** on 2026-10-16. Other app entitlements remain unverified.
- Account username was entered locally. It is not included here; do not print private profile metadata to recover it. The auth API supplies it internally.
- Password and Steam Guard codes were entered directly into SteamCMD. They were not supplied in chat, stored as game settings or placed in command arguments by AlphaGSM. Raw cached tokens must stay private.
- Interactive renewal script: `/home/cosmosquark/.alphagsm-private/login-byo-local.sh`.
- Auth-only config for that script: `/home/cosmosquark/.alphagsm-private/byo-local-auth.conf`.
- Profile root directories use `0700`; metadata/cache files use `0600`, with owner execute permission retained for runtime executables. Operations hold a per-profile lock and clean up interrupted SteamCMD process groups.
- Cache discovery supports exactly the profile-contained `home/Steam/config/config.vdf` and legacy `runtime/config/config.vdf`. The real local login used the first layout. Commit `0da848f3` fixed the prior false missing-session report without moving/exposing cache contents.
- Private session/runtime stays on the protected Linux home filesystem. SSD is NTFS3 with shared permissions, which fails the auth trusted-parent policy. Never weaken those checks or copy profiles onto the SSD, into Git, backups, exports or evidence.
- `status` is only a local-presence check; actual acquisition proves app access for that specific app. Acquisition suppresses raw SteamCMD output and disables credential prompts. No anonymous fallback.
- No desktop Steam installation is required for this Linux SteamCMD flow.

Safe status command:

```bash
RUN=/media/cosmosquark/SSD/sector_alpha/github/AlphaGSM/.local-tests/byo-file-helpers/run
"$RUN" steam-auth status owned
```

Only when real acquisition requires session renewal, have the operator run this in their own interactive terminal:

```bash
bash /home/cosmosquark/.alphagsm-private/login-byo-local.sh
```

Never request the password, Guard code or session token in chat. Do not log out/delete the working profile just to test status.

## Wrapper/config isolation

The SSD `run` wrapper explicitly runs this feature worktree using the verified Python. It sets:

```text
ALPHAGSM_CONFIG_LOCATION = <SSD test root>/alphagsm.conf
ALPHAGSM_USERCONFIG_LOCATION = <SSD test root>/state/user.conf
TMPDIR = <SSD test root>/tmp
```

Its system config selects:

```text
[core] alphagsm_path = /home/cosmosquark/.alphagsm-private
[core] userconf = <SSD test root>/state
[server] datapath = <SSD test root>/state/servers
[downloader] db_path = <SSD test root>/state/downloads.txt
[downloader] target_path = <SSD test root>/downloads
[screen] screenlog_path = <SSD test root>/state/logs
[screen] sessiontag = AlphaGSM-BYO-SSD-Local#
[screen] keeplogs = 1
```

Bulk game files, public caches, staging, logs and ordinary manager metadata stay on SSD. Private auth stays in Linux home. Use this wrapper rather than the original checkout's CLI/default config. Do not repurpose shell `HOME`/`CODEX_HOME`.

## Implemented code and behavior

- All 42 file-based BYO modules have package-local `byo_assets.json` recipes/guidance. Nine support managed import; the other 33 are manual/sentinel-only until a complete authoritative layout is understood. Do not infer a full distribution from a single matching sentinel.
- `src/utils/byo_files.py`: recipe loading/expansion, game-specific file/content checks; source casing can be insensitive, installed checks follow native casing. CoD accepts equivalent map archive member formats. Absolute ETS2/ATS configuration homes support inspection but remain manual-only for mutations.
- `src/utils/asset_import.py`: allowlisted directory/archive imports/exports with selected-content validation, ownership hashes, conflict protection and transactional publication. Operator originals stay unchanged.
- `src/utils/byo_acquire.py`: explicit declared SteamCMD source acquisition into disposable SSD staging, required-content validation and allowlisted import; full app/depot may be downloaded over the network, only selected files are retained.
- `src/utils/steam_auth.py` and `src/utils/steamcmd.py`: private reusable Linux sessions, shared profile-name validation, no password storage or anonymous fallback, private output suppression and process-group/lock handling.
- `src/utils/steam_library.py`: `find_installed_app(steam_dir, app_id)`. Read-only bounded public Steam app/library manifest discovery, explicit `steamapps` restriction, modern/legacy library lists, missing/duplicate/unsafe-path rejection. No account-cache reads or recursive Steam scans.
- `src/server/assets.py` + `src/server/server.py`: `setup --auth-profile NAME`, `setup --steam-dir PATH`, prior `setup --assets PATH`. Explicit source selectors are mutually exclusive and consumed before game configure/install. Host/port checks precede the stopped-server file phase; engine install follows only successful file preparation.
- Setup stores only `steam_auth_profile: owned` after successful acquisition or valid installed-file checks. Later setup reuses it if files are missing, skips Steam when files are complete, and retains the old name on acquisition failure. Explicit local sources override it for that invocation. No selector/no remembered profile preserves the old engine/manual setup flow.
- `set steam_auth_profile NAME` validates the shared name/eligible recipe; `set steam_auth_profile DELETE` clears it idempotently, including stale references. Manager handling bypasses game validation/config-sync/postset. Nested values/credential objects are rejected.
- New Steam setup options require an explicit managed recipe with exactly one declared SteamCMD source. Other provider/auth-gated modules were not globally migrated.
- `src/utils/archive_install.py`: optional exact `skip_relative_files` during copying/install; default empty for existing modules. Q3's `Q3_CLIENT_ONLY_ENGINE_FILES` omits 11 known loose client executable/renderer/cgame/UI files. It retains the selected executable, server game modules and all content archives/maps/resources. It never deletes existing operator files.

## Q3 results: completed and stopped

Tag: **`byossdq3`**. Install: `<SSD test root>/servers/q3`. Backend: **process**. Steam source: AppID **2200**, platform **windows**, private profile **owned**.

- Public depot-size preflight reported 513,401,161 bytes; SSD had about 469 GB free and private home about 27 GB free at preflight. Recheck space before each new game.
- Authenticated `setup -n --auth-profile owned` succeeded. Nine `baseq3/pak0.pk3` through `pak8.pk3` were retained, totaling 505,570,007 selected bytes; all ownership hashes matched. Disposable full-game staging was removed.
- Those intact content packs contain **36 distinct BSP maps**.
- `assets check --json` and doctor passed. Stored manager metadata contains profile name `owned`, not credentials.
- Repeated `setup -n` reused complete assets without starting SteamCMD.
- Dedicated engine selection was reinstalled from the existing public engine cache. All 11 client-only loose files were omitted; dedicated executable plus base/missionpack server game modules remained. All nine PK3 hashes/36 maps were unchanged. The temporary prior-engine backup was removed after success.
- Native lifecycle passed twice, including after engine filtering: start, running status, `query`, `info`, `info --json`, stop and stopped status.
- Actual endpoint: **UDP `127.0.0.1:27960`**, protocol **`quake`**. Returned name `AlphaGSM byossdq3`, map **`q3dm17`**, **0/8 players**.
- Final verification: no owned executable process remains, UDP 27960 can be bound again, status reports not running.
- Docker was **NOT_RUN**. No external/public endpoint validation was performed. Existing native query/info hooks needed no network-related changes.
- Q3 Steam source `live_validated` is true; its manual source remains unvalidated.

## RTCW results: completed and stopped

Tag: **`byossdrtcw`**. Install: `<SSD test root>/servers/rtcw`. Backend: **process**. Steam source: AppID **9010**, platform **windows**, private profile **owned**. Port **27961** because `byossdq3` still claims 27960.

- Authenticated setup imported the allowlisted packs. The first start exited because ioRTCW 1.51c's dedicated `FS_CheckPak0` requires retail `main/pak0.pk3` even after all six `mp_pak` files are present. `patch-data-141.zip` was not merged: overlapping installed multiplayer packs already matched that archive, and the zip also contains PunkBuster and client binaries.
- The managed recipe now requires `main/pak0.pk3` plus the 14 multiplayer PK3 files. A second authenticated setup added the 315,823,656-byte retail pack (4,775 packed files) and preserved every earlier pack hash. Repeat setup then skipped SteamCMD. Staging was removed. `assets check` was ready.
- The dedicated engine install omits known loose client executables, renderers and client-only modules. `fs_basepath` and `fs_homepath` are `.` so process and Docker launches stay inside the install directory. The existing `~/.wolf` tree was unchanged.
- Native lifecycle passed: start, running status, `query`, `info`, `info --json`, stop.
- Actual endpoint: **UDP `127.0.0.1:27961`**, protocol **`quake`**. Returned name `AlphaGSM byossdrtcw`, map **`mp_beach`**, **0/20 players**. A direct A2S probe timed out while the Quake status response succeeded.
- The install retains 15 multiplayer BSP maps and the retail pack's 32 campaign BSP maps. Only `mp_beach` was loaded in the live query.
- Final verification: no owned `iowolfded.x86_64` process remains and UDP 27961 can be bound again.
- Docker was **NOT_RUN**. No external/public endpoint validation was performed.
- RTCW Steam source `live_validated` is true; its manual source remains unvalidated.

Credential-free evidence under `<SSD test root>/results/rtcwserver/`: `lifecycle-pak0.json`, `setup-auth.log`, `setup-pak0.log`, `setup-reuse.log`, `assets-check.json`, `query-pak0.log`, `info-pak0.log`, `info-json-pak0.log`, `status-pak0.log`, and `stop-pak0.log`.

Credential-free evidence under `<SSD test root>/results/q3server/`:

- `2026-10-16-auth-first.json`: overall results, selected hashes/maps, acquisition commit `c635d700`, final behavior commit `a1e2aebb`.
- `setup-auth.log`, `setup-reuse.log`, `setup-server-payload.log`.
- `engine-selection-result.json`, `lifecycle-result.json`.
- `start.log`, `status.log`, `query.log`, `info.log`, `info-json.log`, `stop.log`, `final-status.log`.

Local helpers in `<SSD test root>/tmp/`: `q3_app_size.py`, `q3_engine_reinstall.py`, `q3_lifecycle.py`. These are scratch test helpers, not the product installer. Product behavior is checked into the source files listed above. Do not blindly rerun the engine-reset helper: it was written for the original full-client engine bytes and its retired backup has been removed. Q3 is already validated; retest only when relevant changes justify it.

## Exact queue and next work

Canonical campaign files in the managed worktree:

- `docs/superpowers/plans/2026-10-16-byo-local-validation.md`
- `docs/superpowers/plans/2026-10-16-byo-local-validation.json`
- `docs/superpowers/specs/2026-10-16-auth-first-byo-setup-design.md`
- `docs/superpowers/plans/2026-10-16-auth-first-byo-setup.md`

The JSON has all 42 exact module/tag/manifest/guide/directory/source records, independent acquisition/file/lifecycle/Docker/content results, and explicit network/status/module-review fields. Q3, RTCW, original Call of Duty, United Offensive, and Call of Duty 2 have passing process outcomes. Preserve order and evidence.

First six: Q3 2200 → RTCW 9010 → CoD 2620 → **CoD United Offensive** (base app 2620 plus expansion app 2640) → CoD2 2630 → CoD4 7940. All declared sources use Windows owned-game assets. Downloading original CoD base files is not a full UO pass.

Next three: ET:Legacy owned ET assets, ETS2 client exports, ATS client exports. Steam login cannot generate truck-simulator `export_server_packages` outputs. The remaining 33 require complete manual distributions until their source/layout is verified. Three non-file prerequisites (Astroneer endpoint, Quake Live entitlement, Life is Feudal database) are outside the 42-file-helper queue.

Original Call of Duty, tag `byossdcod`, module `codserver`, Steam AppID 2620, is stopped on UDP 28960. Native Quake `getstatus` returned `AlphaGSM byossdcod`, map `mp_carentan`, 0/20. Evidence is `results/codserver/lifecycle.json`. Docker and external reachability were not run. Do not reuse UDP 27960, 27961, or 28960.

United Offensive, tag `byossdcoduo`, module `coduoserver`, is stopped. Local integration on UDP 49440 answered native Quake `getstatus` for `mp_brecourt`. Evidence is `results/coduoserver/lifecycle.json`. Docker and external reachability were not run. Do not reuse UDP 27960, 27961, or 28960.

Call of Duty 2, tag `byossdcod2`, module `cod2server`, is stopped. Local integration on UDP 43511 answered native Quake `getstatus` for `mp_toujane`. Evidence is `results/cod2server/lifecycle.json`. Docker and external reachability were not run. Do not reuse UDP 27960, 27961, or 28960.

Call of Duty 4, tag `byossdcod4`, module `cod4server`, Steam AppID 7940, is complete on the process runtime and stopped. Local integration passed in 804.69s. CoD4x 21.2 `cod4x18_dedrun` answered native Quake getstatus on UDP 56171, map `mp_crash`, hostname AlphaGSM lacod4server. The published tree has 21 `zone/english/mp_*.ff` maps, `iw_00.iwd` through `iw_13.iwd`, and seven English localized IWDs. Docker and external reachability were not run. Do not reuse UDP 27960, 27961, 28960, 49440, 43511, or 56171.

ET: Legacy is blocked. It needs owned `etmain/pak0.pk3`, `pak1.pk3`, and `pak2.pk3`, and those packs are not on this machine. Euro Truck Simulator 2 and American Truck Simulator are blocked on `server_packages.sii` and `server_packages.dat`. The later manual rows are recorded in the validation JSON as `BLOCKED_MISSING_OWNED_FILES` or `BLOCKED_NO_NATIVE_QUERY`. Do not download retail game archives and do not invent query protocols.

Space Station 14 is complete on the process runtime and stopped. Local integration with `./run_local_tests.sh integration --server ss14server --public` passed in 27.06s. Robust status on TCP/UDP 47183 reported hostname AlphaGSM lass14server, 0 players, and max_players 30. The process runtime used a user-local .NET 10.0.13 install at `/home/cosmosquark/.dotnet`. Docker and external reachability were not run.

ET: Legacy is complete on the process runtime and stopped. Local integration passed in 14.46s. A follow-up query on UDP 57831 reported Quake status, hostname ET: Legacy Host, map oasis, and 0/24. Setup staged only pak0.pk3, pak1.pk3, and pak2.pk3 from cdn.splashdamage.com. The six stock maps are present. Docker was not run.

Alien Arena is complete on the process runtime and stopped. Anonymous Steam app 629540 mounted no depots. Setup linked the Debian/Ubuntu alien-arena packages. Quake II status on UDP 53777 reported hostname AlphaGSM laalienarenaserver, map dm-deathray, and 0/8. Docker was not run.

Foundry is complete on the process runtime and stopped. Anonymous Steam app 2915550 installed the Windows dedicated server. Wine launched `FoundryDedicatedServer.exe`. A2S on UDP 27016 reported hostname AlphaGSM lafoundryserver, map Procedural, and 0/32. The game port was UDP/TCP 51535. Integration passed in 152.80s. Docker was not run. The container family is still `steamcmd-linux`.

Starbound is complete on the process runtime and stopped. Anonymous app 211820 mounts no depots. Profile `owned` installed `linux/starbound_server`. A2S on UDP 50333 reported hostname AlphaGSM lastarbound, map Unknown, and 0/8. Integration passed in 171.27s. Docker was not run.

Nuclear Dawn is complete on the process runtime and stopped. Profile `owned` installed app 111710, including hydro.bsp. The first scripted lifecycle timed out because NTFS left srcds_linux non-executable. prestart now restores that bit. A later start answered A2S on UDP 36736: hostname AlphaGSM Nuclear Dawn, map hydro, 0/32. Docker was not run.

SourceForts Classic is complete on the process runtime and stopped. Anonymous app 244310 branch previous2021 plus the official ModDB 1.0 RC7 tree answered A2S on UDP 58844: A2S hostname Sourceforts Classic 1.0 [BUILD], map sf_astrodome, 0/32. The public local integration passed in 47.02s. prestart disables empty hibernation, aliases bin/*_srv.so, and restores the srcds execute bit. Docker was not run.

Zombie Master: Reborn is complete on the process runtime and stopped. Anonymous app 244310 branch previous2021 plus the official Linux archive linked from zombiemaster.dev answered A2S on UDP 42202: hostname AlphaGSM Zombie Master: Reborn, map zm_docksofthedead, 0/16. The public local integration passed in 46.64s. This build reports sv_hibernate_when_empty as an unknown command. Docker was not run.

GoldenEye: Source stays blocked. The project's only 5.0.6 server archive returned HTTP 403 from Cloudflare on 2026-10-17. Windows app 310 was not installed. No native Linux srcds_run tree is published.

GRAV is complete on the process runtime and stopped. Anonymous app 332500 mounts no depot. Profile owned installed the Win32 tree. Wine answered A2S on UDP 41002: hostname lagrav, map Reborn Update 9.8.1, 0/255. Game port 41000, peer port 41001. Docker was not run.

SteamCMD is idle. The remaining rows are blocked on missing owned exports, missing native query parsers, or official downloads that are not available. Do not reuse UDP 27016, 27960, 27961, 28960, 36736, 41000, 41001, 41002, 42202, 43511, 47183, 49440, 50333, 51535, 53777, 56171, 57831, or 58844. UDP 27015 is an unrelated L4D2 listener. Do not reserve 27005; that client port is on the L4D2 command line. Half-Life mods ahl, bb, ns, ts, and vs stay blocked: app 90 does not install their trees, and the checked-in ModDB, ENSL, ironoak, and vsmod URLs are not fetch targets.

For each row: inspect recipe/help/settings and disk budget → configure a unique stopped SSD instance → preferred authenticated setup (or its legitimate local/export source) → verify complete server files/content → doctor → bounded real native protocol readiness, status/query/info/JSON → fix/retest code when needed → finally stop and prove all owned processes/listeners gone → update queue, guide, tracker/changelog. External missing input is an explicit blocker, never a pass. Keep secrets out of evidence.

## Verification and environment pitfalls

Last full behavior gate at `a1e2aebb`:

```bash
cd /home/cosmosquark/.codex/worktrees/byo-file-helpers/AlphaGSM
PYTEST_XDIST_AUTO_NUM_WORKERS=4 make test PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python
make lint PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python
```

Results: **10,235 passed, 4 skipped**, 67.36 seconds; production pylint **10.00/10**; 35 skills valid. Logs: `/tmp/alphagsm-complete-content-unit-final.log`, `/tmp/alphagsm-complete-content-lint.log`. All code tasks had spec/quality review, and combined code/docs review approved. Subsequent query/status policy changes were docs/queue only; JSON integrity and `git diff --check` were validated, not another live run.

- Default Python has an incompatible similarly named crontab package; use the verified venv with `python-crontab`. A default-environment lint run produced unrelated CronTab signature errors (9.99); do not patch working production APIs to accommodate that environment.
- Auth unit tests need actual host ownership semantics. The sandbox maps root ownership and causes `_check_ancestor('/')` failures; host execution passes. Do not weaken trusted-parent checks to make sandbox tests pass.
- A full-suite test-order failure was reproduced: downloader tests reload the package, making a fake's late-imported `DownloaderError` a different class from auth's captured dependency. Commit `a1e2aebb` makes the fake raise `auth.DownloaderError`. Production code/security/sanitization assertions were unchanged. Ordered regression: 130 passed, then full suite passed.
- Test files intentionally exercising private security APIs have pre-existing protected-access pylint warnings. Official repository lint covers production; do not confuse those warnings with a failed production gate.
- Full authenticated CI integration and Docker lifecycle validation were not run. Do not claim them from unit or native-process success.

## Commits of interest

- `9412263b`: initial BYO/private auth implementation.
- `358e8b1c`: native installed casing versus insensitive source matching.
- `b3dba968`: CoD equivalent map archive member alternatives.
- `698142ed`: absolute truck-sim home inspection/manual mutations.
- `0da848f3`: real isolated-home SteamCMD cache recognition.
- `113b941f`, `4e9303b1`: public Steam library resolver and portable reserved-name fix.
- `c635d700`: auth-first setup, saved profile names and Steam-directory alternative.
- `9cbfb131`: Q3 owned Steam acquisition marked locally validated.
- `49daf65c`: dedicated Q3 engine payload selection, preserving full content.
- `a1e2aebb`: auth test fixture import-order correction.
- `da219845`: full docs/campaign and Q3 evidence closure.
- `278bd5bd`: explicit per-game native port-query/status/module-fix completion rules.

This handoff itself is saved in a later documentation-only commit. Inspect `git log -1` for its hash. The managed worktree is preserved; all local test servers should remain stopped when handing off.
