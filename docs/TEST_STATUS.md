# Integration Test Status

Last updated: 2026-09-09

## Summary

Tracker note: on 2026-06-27 the live support gate files were reconciled with the
documented `ENABLED (AUTH)` / `ENABLED (BYO)` rows and CI now validates that
`docs/TEST_STATUS.md`, `disabled_servers.conf`, `enabled_byo_servers.conf`, and
`enabled_auth_servers.conf` stay in sync.

| Status   | Count |
|----------|-------|
| PASSED | 141 |
| ENABLED (AUTH) | 48 |
| ENABLED (BYO) | 45 |
| DISABLED | 3 |
| SKIPPED | 0 |

## Environment Coverage

- Ubuntu 24.04 is the full game-server lifecycle validation baseline for this
  tracker, including process and Docker lanes where each runtime is supported.
- Windows and macOS currently run representative Minecraft backend integration
  checks only; they do not yet validate the complete game-server matrix.
- Broader lifecycle coverage on newer and other Linux distributions, Windows,
  and macOS remains future work.
- Corrections described as pending replacement GitHub CI do not record a new
  integration or smoke pass until that workflow completes successfully.

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **ENABLED (AUTH)** — Supported server module that still requires provider-managed authentication, credentials, tokens, licenses, or provisioning before setup/start can fully succeed.
- **ENABLED (BYO)** — Supported server module that still requires an explicit operator-provided prerequisite such as owned assets, exported client files, an external service, or a direct URL.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.

## Counter-Strike Split

- `counterstrike2` and `cs2server` are the current CS2 surface. They now have a dedicated integration test and smoke runner, and they are not listed in `disabled_servers.conf`.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by Steam app `740` and are disabled.

## Pending Replacement CI (Not Support States)

- Conan Exiles now installs the official native Linux depot and runs through
  the shared `steamcmd-linux` family. The previous Windows server reached
  startup under Wine but crashed in `xaudio2_9.dll` even with `-nosound`.
  Existing WindowsServer settings and the legacy save database migrate only
  when native targets are absent. Docker now runs the root-refusing binary as
  the invoking host user. Replacement lifecycle validation is pending.
- Onset now exposes its install root to the native loader so the bundled
  `libsteam_api.so` resolves. Readiness now requires its loaded marker and the
  documented TCP file listener after private query sockets did not answer.
  Survive the Nights now copies required missing
  files such as `TpPresets.json` from its shipped configuration templates while
  preserving operator files. Nightingale's first bootstrap reached level and
  navigation loading after the old five-minute deadline, so smoke validation
  now allows ten minutes, retains application/runtime diagnostics, and uses
  host networking to reach the native server's loopback-bound HTTP status
  listener. These corrections await replacement CI lifecycle validation.
- ARK: Survival Ascended now enables and publishes its TCP RCON service for
  `query` and `info`. Its prior A2S timeout was a protocol mismatch: current ASA
  uses EOS and documents the old query port as deprecated. Fresh and legacy
  instances receive a private generated password before RCON is exposed, while
  operator-defined credentials are preserved. Space Engineers now passes its
  mounted container path to `-path` instead of a host-only path.
  Both corrections await replacement CI lifecycle validation.
- CODWAW requires its Quake status reply. Night of the Dead, No One Survived,
  Icarus, and Soulmask retain their previously validated generic TCP health
  surfaces on the managed game port because their current Linux/Wine servers do
  not answer A2S. Failed runners retain application/runtime logs before cleanup.
- Further September 9 repairs correct Soldat's root-user exit, native player
  limit/configuration and status query; publish Project CARS' query port; apply
  Ground Branch's documented launch and wildcard bind syntax, then validate its
  current SteamSockets game listener because Proton does not expose local A2S;
  and provide Battle Cry of Freedom's Wine display. Failed `send` commands now
  capture bounded runtime diagnostics.
  BCoF's native port settings remain unverified. These changes have unit coverage
  and await CI lifecycle validation; no support state is promoted.
- Silica now synchronizes its native XML under an isolated persistent home,
  retaining existing mode/map/admin settings and using the configured Steam
  query port for readiness. The XML layout is backed by publisher guidance and
  maintained server implementations; replacement CI must confirm the A2S reply.
- September 9 launch repairs supply ASKA and Sunkenland with Xvfb and preserve
  Saleblazers' unattended `-headless` configuration launch. Runtime diagnostics
  now tolerate inaccessible Steam directories and show local listeners and
  allowlisted numeric port arguments. Replacement CI validation is pending.
  Heat still exits in `AsyncConsoleReader.set_InputFormat` before startup and
  does not yet have a verified runtime fix.
- Argo and Life is Feudal now use their native Steam query listeners and claim
  adjacent ports. Life is Feudal also receives its documented world argument,
  native world/database configuration, and managed database routing for Docker.
  These corrections await replacement CI and do not change support states.
- Colony Survival reaches world creation and Steam registration but its old
  query endpoint refuses connections. The [upstream 0.17/0.18 config update](https://github.com/pipliz/ColonySurvival/commit/23c8dad2fa7debaf38e802bc6472914bf75f68c0)
  removed `ServerQueryPort`; older Docker and query-client port maps predate
  that change. A current listener/protocol still needs CI evidence.

- September 8 smoke/CI repairs correct skip reporting, Source smoke protocol
  readiness, artifact upload retry, Tower Unite/Warfork Steam library exposure,
  Unturned/STN native ports, and Wine query protocols for
  NOTD and No One Survived. Icarus and Soulmask continue to use their validated
  generic TCP health surfaces. CODWAW now uses its native UDP status protocol.
  ETS2 tests require real exported client packages. These
  changes have local unit coverage and await replacement CI lifecycle results.
  They do not promote any server's support state.
- Fresh [AHL2 Docker diagnostics](https://github.com/SectorAlpha/AlphaGSM/actions/runs/34280455410/job/102247947798)
  show a repeated native glibc `sysmalloc` assertion following Steam client
  initialization. This is distinct from the earlier sleeping-process snapshot;
  no allocator or Steam launch-flag workaround is established yet.

- [PR #36 run 34250522498](https://github.com/SectorAlpha/AlphaGSM/actions/runs/34250522498)
  at `de6777c4` passed unit tests, lint, coverage and all five binary targets.
  Overall it recorded 177 successful and 92 failed checks, including smoke
  batches and isolated game rechecks. TeamSpeak Docker now passes authenticated
  readiness and query, then falls back to TCP on the next info call. Its five
  commands per check exceed the default ServerQuery flood budget when repeated;
  command pacing has unit coverage and awaits CI confirmation. GMod now uses
  its own launcher but fails to reach readiness, like other Source
  Docker lanes. Terraria 1.4.5.8 creates its world and listens, then crashes with
  `ObjectDisposedException` in `DebugNetworkStream` after TCP probes. Those
  Source and Terraria failures remain unresolved; no new game pass is claimed.
  Source diagnosis now adds native query attempts followed by bounded GDB stack
  capture in CI. CSS and GMod process passes provide the comparison; Docker
  sleeping-thread snapshots alone do not establish the cause. Runtime changes
  remain pending that evidence.

- [PR #36 run 34213901844](https://github.com/SectorAlpha/AlphaGSM/actions/runs/34213901844)
  completed at commit `51ad45e4` with 183 successful and 90 failed checks
  (job counts, including rechecks and smoke batches). GMod selected a launcher
  inside `_gmod_content/tf`; TeamSpeak Docker reached TCP readiness but failed
  authenticated ServerQuery; Quake Live could not exec `baseq3/server.cfg` and
  timed out waiting for the older Quake query protocol. Pending fixes prefer
  install-root Valve launchers, recover TeamSpeak credentials from runtime logs,
  and use Quake Live's native config/startup syntax and Steam A2S protocol.
  CSS and related Source Docker Steam-initialization stalls remain unresolved.
  Local verification is limited to unit tests and lint; no support-state
  promotion is claimed before replacement CI proves these game lifecycles.

- [PR #36 run 34155516516](https://github.com/SectorAlpha/AlphaGSM/actions/runs/34155516516)
  passed all five binary acceptance targets. Initial integration artifacts contain
  186 passes, 87 failures and 199 skips (down from 113 initial failures in the
  preceding run). Isolated recheck artifacts contain 85 failures and one pass;
  the remaining Colony Survival recheck also failed in its job log, but GitHub's
  artifact service timed out after five upload attempts. CSS, HL2DM and DODS
  passed their process lifecycle checks; their Docker startup stalls remain open.
  Pending corrections address Quake Live's library path, Quake II's unwritable
  home path, MTA/OHD query routing, Velocity Java selection and Minecraft fixture
  drift. Readiness fail-fast and bounded Docker process diagnostics will expose
  remaining crashes/stalls in replacement CI. These are not new support states.
  Additional pending corrections keep Source launch wrappers, explicitly opt
  fresh Terraria/TShock and Necesse tests into --autocreate, require real GoldSrc
  A2S smoke readiness, and match
  Palworld's actual listening message. Local validation of these corrections is
  limited to unit tests and lint; replacement CI must prove the game lifecycles.

- PR #36 standalone/runtime and CI-integrity changes require fresh CI proof.
  The binary matrix targets Linux x86-64/ARM64, macOS Intel/Apple Silicon and
  Windows x86-64; these targets do not promote existing game support states.
  Integration and real game/backend acceptance for this change run in CI only.
  Signing identities and ASTRONEER heavy-runner/public-IP configuration remain
  external prerequisites; see [the release contract](../DEVELOPERS.md#standalone-release-contract).

These entries are explicitly not `PASSED`. They are intentionally outside the
support-state tables and do not change the summary counts or record a new pass.

| Test | Pending validation |
|------|--------------------|
| ns2server | Process and Docker lifecycle revalidation of the corrected install-root launcher, relative data paths, exact A2S query on `port + 1`, and shutdown checks. |
| ns2cserver | Process and Docker lifecycle revalidation of the corrected `ia32` working directory, relative data paths, exact A2S query on `port + 1`, and shutdown checks. |

## PASSED (141)

| Test | Type |
|------|------|
| ahl2server | SteamCMD (Source) — PASSED; process and Docker lanes use the same runtime-resolved TCP game-port health contract. The current Linux payload does not answer A2S while empty and rejects the hibernation cvar, so integration validates the live TCP endpoint rather than claiming an unavailable A2S surface. |
| argoserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31 on anonymous SteamCMD app `563930`; AlphaGSM launches the shipped `argoserver` binary inside the shared `steamcmd-linux` runtime, syncs `server.cfg` from the managed `servername`, and now validates `query`, `info`, and `info --json` through the native A2S listener on game port plus one. The runtime also claims and publishes both adjacent Steam UDP ports; this correction awaits replacement CI. The stale `server` beta override has been removed because current SteamCMD rejects that branch; public-branch revalidation is pending the replacement CI run. |
| ark | Docker runtime (SteamCMD Linux) — PASSED 2026-06-01; fresh formal integration now proves the old size-based disabled note is no longer the real blocker: anonymous SteamCMD setup for app `376030` completes on the shared `steamcmd-linux` runtime, AlphaGSM launches `ShooterGame/Binaries/Linux/ShooterGameServer` from its real working directory inside the Docker lane as a non-root user with the shared Steam bootstrap mounted into `~/.steam/sdk64/steamclient.so`, and validates real A2S `query`, `info`, and `info --json` on the managed `queryport` instead of the older stale host-process / generic-TCP assumptions |
| arksurvivalascended | Docker runtime (Wine/Proton) — PASSED 2026-05-30; the current correction replaces the deprecated Steam query-port assumption with authenticated Source RCON `ListPlayers` on managed TCP `rconport`. The runtime contract claims and publishes game UDP and RCON TCP; launch enables RCON and keeps the admin password out of query output. Replacement CI validation is pending; this does not record a new pass. |
| armarserver | SteamCMD |
| avserver | SteamCMD |
| archive_backed_installs | Archive |
| bb2server | SteamCMD (Source) — PASSED; process and Docker readiness uses AlphaGSM's real A2S `info --json` response because Docker console logs can omit the traditional Source startup markers |
| btlserver | SteamCMD — Docker runtime uses the shared non-root host-user contract required by the Unreal payload; the current GitHub matrix validates both process and Docker lanes |
| btserver | Docker runtime (SteamCMD Linux) — PASSED; the current contract keeps process and Docker module code aligned, publishes the configured game/query ports, and validates `query`, `info`, and `info --json` through Barotrauma's live Lidgren UDP surface on the primary game port instead of requiring stale A2S behavior from the adjacent query port. |
| bdserver | SteamCMD (GoldSrc), process + Docker — PASSED; the shared Valve query hook now resolves the runtime-reachable host, and integration readiness uses AlphaGSM's A2S `info --json` surface instead of a host-only `screen` log. Replacement CI validation is pending. |
| bmdmserver | SteamCMD (Source), process + Docker — PASSED; integration readiness now uses AlphaGSM's A2S `info --json` surface directly and no longer requires a host `screen` log or guessed localhost query address in the Docker lane. |
| blackwakeserver | Docker runtime (Wine/Proton) — PASSED 2026-05-30; `query`, `info`, and `info --json` use one runtime-agnostic generic `tcp` surface on the managed main port, while `stop` routes through the shared runtime layer. CI now keeps the proven Docker-default lifecycle rather than forcing an unproven host Wine lane; replacement validation of the shared Docker host resolver is pending. |
| ccserver | SteamCMD (Source) |
| citadelserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; anonymous SteamCMD app `489650` and the native Linux payload remain supported, with the validated health contract now declared honestly as generic TCP on the managed game port because the configured queryport did not answer A2S in replacement CI validation. |
| colserver | SteamCMD |
| conanexiles | Docker runtime (SteamCMD Linux) — the official native Linux depot replaces the Wine path that crashed in `xaudio2_9.dll` during current CI. AlphaGSM launches `ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping` as the invoking host user because the binary refuses root, syncs settings under `ConanSandbox/Saved/Config/LinuxServer/`, claims the hardcoded pinger at game port plus one, and retains A2S on the managed `queryport`. Replacement CI validation is pending; this does not record a new pass. |
| counterstrike2 | SteamCMD (Source 2) — PASSED 2026-04-08 |
| csczserver | SteamCMD (GoldSrc) |
| csserver | SteamCMD (GoldSrc) |
| cssserver | SteamCMD (Source) — PASSED; process and Docker readiness uses AlphaGSM's real A2S `info --json` response because Docker console logs can omit the traditional Source startup markers |
| craftopiaserver | SteamCMD |
| cryofallserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale: anonymous SteamCMD setup for app `1061710` installs a real native `.NET 6` dedicated server payload, AlphaGSM stages `Data/SettingsServer.xml` from a managed template, launches `dotnet Binaries/Server/CryoFall_Server.dll loadOrNew` inside the shared `steamcmd-linux` runtime, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed main game port |
| dayofdragonsserver | SteamCMD |
| darkandlightserver | Docker runtime (Wine/Proton) — PASSED 2026-05-30; fresh smoke and integration pass on the branch-local `wine-proton` runtime image once AlphaGSM treats the validated Linux contract honestly: Dark and Light answers `query`, `info`, and `info --json` on the managed main game port as generic `udp`, stop flows through the shared runtime layer, and the Docker-backed Xvfb/software-GL lane no longer depends on a live host `screen` session or the older stale `queryport` A2S assumption. A 2026-07-16 forced process lane stayed alive without opening the UDP surface, so CI now keeps the proven Docker-default lifecycle. |
| deadpolyserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh focused integration now proves the old missing-binary disable note was stale in a narrower way: anonymous SteamCMD setup for app `2208380` installs the real Windows dedicated payload, AlphaGSM stages `DeadPoly/Saved/Config` from the shipped `1 RENAME Config` tree, launches `DeadPolyServer.exe -log -nosteam` under the shared Wine/Proton runtime, and validates `query`, `info`, and `info --json` on the current generic `tcp` health surface at the managed `queryport` |
| dmcserver | SteamCMD (GoldSrc) |
| dodserver | SteamCMD (GoldSrc) |
| dodsserver | SteamCMD (Source) |
| doiserver | SteamCMD (Source) |
| ecoserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-29; AlphaGSM launches Eco offline, stages its Steam/.NET bootstrap, syncs `Configs/Network.eco` side ports, and validates generic `tcp` health on the managed main port. Ubuntu 24.04 process setup correctly rejects a missing `libgdiplus`, so CI now keeps the documented Docker-default lifecycle rather than forcing an invalid host lane. |
| emserver | SteamCMD (Source) — PASSED 2026-05-23; focused integration now reaches real Source log readiness, hibernation-safe `info --json`, A2S query/info, and clean shutdown on the anonymous SteamCMD install path |
| empyrionserver | Docker runtime (Wine/Proton) — PASSED 2026-05-29; the direct `DedicatedServer/EmpyrionDedicated.exe` contract syncs `dedicated.yaml` and uses Empyrion's live STCP TCP listener at `port + 3`. The 2026-07-16 forced host-Proton process exited before readiness, so CI now runs one Docker-default heavy lifecycle and waits on AlphaGSM `info --json` instead of a host-owned log. |
| exfilserver | SteamCMD — PASSED; the server runs as the invoking host user in Docker and `query`, `info`, plus `info --json` use the validated UDP health surface on the managed game port after the current server logs its exact `IpNetDriver` listener instead of assuming A2S on `queryport` |
| fearthenightserver | Wine/Proton — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the Linux/Proton lane once AlphaGSM syncs `Moonlight/Saved/Config/WindowsServer/Engine.ini` and `GameUserSettings.ini`, launches the dedicated server with the real `Pittsburgh_Overworld?listen?Port=...?QueryPort=...?SessionName=...?MaxPlayers=...` map URL instead of the older stale bare-map contract, and treats the live health surface as generic `udp` on the managed game port because the current Linux runtime still does not expose a working A2S listener on `queryport` |
| fofserver | SteamCMD (Source) — PASSED; process and Docker readiness uses AlphaGSM's real A2S `info --json` response because Docker console logs can omit the traditional Source startup markers |
| frozenflameserver | SteamCMD |
| gmodserver | SteamCMD (Source) — PASSED; process and Docker readiness uses AlphaGSM's real A2S `info --json` response because Docker console logs can omit the traditional Source startup markers |
| hl2dmserver | SteamCMD (Source) |
| hldmserver | SteamCMD (GoldSrc) |
| hldmsserver | SteamCMD (Source) |
| heatserver | Wine/Proton — PASSED 2026-05-29; a fresh SteamCMD-managed lifecycle now passes on `release_v1` after AlphaGSM bootstraps missing `Configuration/ServerSettings.cfg` on first launch, syncs `portNumber` / `steamAuthPort` / `maxPlayers` / `levelName` into the native config, reads readiness from `Logs/Console*.txt`, and proves A2S `query`, `info`, `info --json`, and clean shutdown on the managed `queryport` |
| hurtworldserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale: anonymous SteamCMD setup for app `405100` installs the real native Linux dedicated payload, AlphaGSM prefers `Hurtworld.x86_64` while falling back to the shipped Linux executables, launches the real headless `-exec "host ...;queryport ...;maxplayers ...;servername ..."` contract inside the shared `steamcmd-linux` runtime, and validates A2S `query`, `info`, and `info --json` on the managed `queryport` |
| hzserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale in a narrower way: anonymous SteamCMD setup for app `2728330` installs a Windows-only dedicated payload, AlphaGSM launches the real `HumanitZServer-Win64-Shipping.exe` binary inside the shared `wine-proton` runtime, mirrors `ServerName` and `MaxPlayers` into `HumanitZServer/GameServerSettings.ini` from the shipped reference config, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed `queryport` instead of the older stale Linux-binary assumption |
| icarusserver | Docker runtime (Wine/Proton) — PASSED 2026-05-30; fresh integration and smoke now both pass on the branch-local `wine-proton` runtime image once AlphaGSM treats the validated Linux contract honestly: anonymous SteamCMD setup for app `2089300` succeeds, the server stays up in the shared Docker-backed Xvfb/software-GL lane, and `query`, `info`, plus `info --json` all use the live generic `tcp` surface on the managed main port instead of the older stale log-marker and A2S assumptions |
| jc2server | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; anonymous SteamCMD app `261140`, `Jcmp-Server`, staged default scripts/config, and generic `tcp` health on the managed main port remain the supported contract. The forced process lane started without exposing that surface, so CI now keeps one Docker-default lifecycle. |
| jc3server | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh smoke and focused integration now prove the old disabled missing-executable note was stale: anonymous SteamCMD setup for app `619960` installs the current native Linux dedicated server, AlphaGSM launches the real `Server` binary inside the shared `steamcmd-linux` runtime as a non-root user with the host SteamCMD `steamclient.so` bootstrap mounted into `~/.steam/sdk64`, syncs the native `config.json` before start, and validates `query`, `info`, and `info --json` on JC3MP's real TCP health surface at `httpPort = port + 3` rather than the older stale CLI/A2S assumptions |
| kerbalspaceprogramserver | Docker runtime (SteamCMD Linux) — PASSED 2026-06-01; fresh smoke and focused integration now prove the old SteamCMD/platform skip note was stale: AlphaGSM downloads the Linux LunaMultiplayer release directly, launches the native `LMPServer-linux-x64/Server` host inside the shared `steamcmd-linux` runtime, creates first-run `Config/ConnectionSettings.xml` and `GeneralSettings.xml` when the upstream archive has not generated them yet, syncs the managed port, server name, and max players before start, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed main game port |
| kf2server | SteamCMD |
| l4dserver | SteamCMD (Source) |
| l4d2server | SteamCMD (Source) — PASSED 2026-06-01; app `222860` installs anonymously when AlphaGSM stages the Windows depots first and then applies the Linux depots into the same server tree. Process and Docker readiness uses the real A2S `info --json` response on the managed game port because Docker console logs can omit the traditional Source startup markers. |
| lastoasisserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-30; anonymous SteamCMD app `920720`, the native `MistServer-Linux-Shipping` payload, and generic `tcp` health on the managed main port remain the supported contract. The 2026-07-16 forced process lane mounted content but never opened that surface, so CI now keeps one Docker-default lifecycle. |
| longvinterserver | Docker runtime — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the shared `steamcmd-linux` runtime image once AlphaGSM seeds `Longvinter/Saved/Config/LinuxServer/Game.ini` from the shipped `.default`, syncs `ServerName` / `MaxPlayers`, launches `LongvinterServer.sh` inside the container as the mounted server-directory owner instead of root, and treats the live health surface as generic `udp` on the managed game port instead of the older stale A2S `queryport` assumption |
| minecraft_bedrock | Docker runtime (service-console) — PASSED 2026-05-30; fresh focused integration now passes on the rebuilt branch-local `service-console` runtime image after AlphaGSM switches Bedrock setup from the stale JavaScript-page assumption to a direct browser-header archive fetch, keeps Docker-first lifecycle coverage on the shared runtime family, and uses Docker-stop for the container-backed stop path because Bedrock echoes console `stop` input without exiting cleanly under the shared exec-console path |
| minecraft_paper | Direct download |
| minecraft_bungeecord | Direct download — PASSED 2026-05-30; fresh focused integration now proves the tracker row was stale: AlphaGSM resolves the latest successful upstream BungeeCord Jenkins build automatically during `setup`, generates `config.yml`, and passes `query`, `info`, `info --json`, `status`, and clean shutdown on the managed SLP/TCP proxy port without requiring a bring-your-own jar URL |
| minecraft_vanilla | Direct download — PASSED 2026-05-16; the integration helper selects the newest release compatible with the installed Java runtime, and setup seeds managed properties plus the accepted-EULA file without leaving a bootstrap JVM alive before the real start lifecycle |
| minecraft_velocity | Direct download |
| minecraft_waterfall | Direct download |
| medievalengineersserver | Docker runtime (Wine/Proton) — PASSED 2026-06-03; anonymous SteamCMD setup for app `367970` completes, AlphaGSM stages `instance-data/MedievalEngineers-Dedicated.cfg`, and validates `query`, `info`, and `info --json` on the generic `tcp` health surface at the managed game port. The host Proton path now uses Xvfb as the Docker path already did, preventing the dedicated server's immediate window-handle crash. |
| memoriesofmarsserver | SteamCMD |
| miscreatedserver | Docker runtime (Wine/Proton) — PASSED 2026-05-29; the supported Linux path reads `user/server.log` and uses generic `tcp` health on the managed main port. CI now keeps one Docker-default lifecycle rather than duplicating an unproven host-Proton lane. |
| codwawserver | Docker runtime — PASSED 2026-05-30; AlphaGSM drives the archive-backed install through the shared `steamcmd-linux` runtime and validates `query`, `info`, plus `info --json` through the native Quake-style UDP status protocol on the managed game port |
| mumbleserver | Docker runtime — PASSED 2026-05-18; standard integration/smoke use the shared `simple-tcp` Docker runtime because upstream does not publish an anonymous standalone Linux server binary. Process mode remains available for operators with a host `mumble-server`/`murmurd` package, but CI keeps one Docker-default lifecycle. |
| mtaserver | Docker runtime — PASSED 2026-05-30; fresh focused integration and smoke now both pass on the branch-local `steamcmd-linux` runtime image once AlphaGSM auto-installs the official `baseconfig.tar.gz` payload, syncs `mods/deathmatch/mtaserver.conf` before launch, disables `ase` so no unmanaged `port + 123` listener is required, and aligns `query`, `info`, and `info --json` to MTA's real built-in HTTP listener on `httpport = port + 2` instead of the older stale ncurses/A2S assumptions |
| mordserver | SteamCMD |
| necserver | SteamCMD |
| nmrihserver | SteamCMD (Source) |
| noonesurvivedserver | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on the Docker-backed Linux `wine-proton` lane once AlphaGSM uses the shared Xvfb/software-GL container entrypoint and aligns `query`, `info`, and `info --json` to the current generic `tcp` status surface on the managed main port instead of the older stale A2S `queryport` expectation |
| notdserver | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on the Docker-backed Linux `wine-proton` lane once AlphaGSM mirrors `ServerSettings.ini` into `LF/Saved/Config`, adds the required `-DisableAntiCheat` Linux launch flag, and aligns `query`, `info`, and `info --json` to the current generic `tcp` status surface on the managed main port instead of the older stale A2S `queryport` expectation |
| nightingale | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; anonymous SteamCMD app `3796810` and non-root `NWXServer.sh` launch remain the supported path. The current branch now passes the official `-port` and `-statusPort` arguments, binds the HTTP status listener to `0.0.0.0`, and validates `query`, `info`, and `info --json` through `/status` on `queryport` instead of the stale generic-TCP assumption. Replacement CI validation is pending. |
| ohdserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale: anonymous SteamCMD setup for app `950900` installs the real native Linux dedicated payload, AlphaGSM launches the shipped `HarshDoorstopServer.sh` wrapper or falls back to the nested `HarshDoorstop/Binaries/Linux/HarshDoorstopServer-Linux-Shipping` binary, mounts the shared Steam bootstrap into `~/.steam/sdk64/steamclient.so`, and validates A2S `query`, `info`, and `info --json` on the managed `queryport` instead of the older stale main-port / executable-name assumptions |
| opforserver | SteamCMD (GoldSrc) |
| outpostzeroserver | Wine/Proton — PASSED 2026-05-29; AlphaGSM mirrors the shipped `RunServer.bat` contract by launching `WindowsServer/SurvivalGameServer.exe RedPlanet ... -log`, syncing `Saved/Config/WindowsServer/Game.ini`, seeding `steam_appid.txt` beside the Win64 binaries, claiming both documented game-client UDP ports, and waiting for the real post-load discovery surface before `query`, `info`, and `info --json` on generic `udp` at `port + 1` |
| palworld | SteamCMD Linux, process + Docker — PASSED; the corrected contract publishes and launches only Palworld's documented UDP game port, removes the invented query-port argument, and uses generic UDP `query`, `info`, and `info --json` on the managed game port. Fresh validation of this correction is pending the replacement CI run. |
| primalcarnageextinctionserver | Wine/Proton — PASSED 2026-05-28; the corrected dedicated launch argv now feeds the `PC-Docks?...?bIsDedicated=true` map URL directly to `PrimalCarnageServer.exe`, focused smoke/integration reach `LoadMap: PC-Docks`, `Game class is 'PCTeamDeathMatchGame'`, and `NetMode is now 1`, A2S/info succeed on the managed `queryport`, and `stop` closes the live UE3 ports cleanly |
| pcarserver | PASSED 2026-05-23; standard smoke and focused integration now both pass, with readiness driven by `info --json` protocol `a2s` on the derived query port (`port + 1`) |
| projectzomboid | SteamCMD |
| q2server | Direct download — PASSED 2026-05-18; setup builds Yamagi Quake II from source, stages the official demo `baseq2` data, and defaults fresh servers to `demo1`. Process and Docker query/info use the dedicated Quake II `status` protocol, while Docker runs as the invoking host user because Quake II refuses root execution. |
| qwserver | Direct download — PASSED 2026-05-18; setup stages the public nQuake shareware, KTX runtime, configs, and core maps needed for anonymous MVDSV installs. GitHub CI authenticates release metadata resolution, process and Docker launch with `-game ktx`, and the shared Quake image supplies MVDSV's required `libcurl.so.4` before validating the QuakeWorld `status` protocol. |
| pvkiiserver | SteamCMD (Source) — PASSED; process and Docker readiness uses AlphaGSM's real A2S `info --json` response because Docker console logs can omit the traditional Source startup markers |
| pvrserver | Docker runtime — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the shared `steamcmd-linux` runtime image, and AlphaGSM `query`, `info`, and `info --json` correctly use Pavlov VR's helper UDP status port (`port + 400`) instead of the older stale A2S expectation |
| vrserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh smoke and focused integration now both prove the old missing-binary disabled note was stale: anonymous SteamCMD setup for app `1829350` installs the real Windows dedicated payload, AlphaGSM stages `Settings/ServerHostSettings.json` from the managed template, launches `VRisingServer.exe` under the shared Wine/Proton runtime with `-persistentDataPath`, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed `queryport` |
| ricochetserver | SteamCMD (GoldSrc), process + Docker — PASSED; the shared Valve launcher now prefers `hlds_run` when available, and integration readiness uses AlphaGSM's A2S `info --json` surface instead of requiring a host `screen` log. |
| rimworldtogetherserver | Direct download |
| rust | SteamCMD Linux, process + Docker — PASSED; the current contract uses game UDP `28015`, RCON TCP `28016`, and explicit Steam query UDP `28017`, passes `+server.queryport`, resolves A2S through AlphaGSM for both runtimes, and no longer waits for a host `screen` log in the Docker lane. Fresh validation of this correction is pending the replacement CI run. |
| satisfactory | SteamCMD |
| saleblazersserver | Wine/Proton (Docker required, process additional) — revalidation pending on the Ubuntu 24.04 GitHub Actions baseline after the Docker launch now enables its 24-bit Xvfb display explicitly. The historical 2026-05-29 process validation used the dedicated `-config ./DedicatedServerConfig.json` launch contract and generic UDP helper port (`port + 1`); do not treat it as fresh Docker proof until the current full lifecycle run is green. |
| silicaserver | SteamCMD |
| scpslserver | SteamCMD |
| scumserver | Docker runtime (Wine/Proton) — PASSED 2026-06-02; anonymous SteamCMD setup for app `3792580` installs the real Windows dedicated payload, AlphaGSM launches `SCUM/Binaries/Win64/SCUMServer.exe` under the shared `wine-proton` runtime, and the validated Linux health surface is generic `tcp` on the managed main game port. The 2026-07-16 forced process lane stayed running without opening that surface, so CI now keeps one Docker-default heavy lifecycle. |
| smallandserver | SteamCMD |
| seserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh focused integration now proves the old missing-binary disable note was stale in a narrower way: anonymous SteamCMD setup for app `298740` installs the real Windows dedicated payload, AlphaGSM launches `DedicatedServer64/SpaceEngineersDedicated.exe` inside the shared `wine-proton` runtime from its required `DedicatedServer64` working directory, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed main game port instead of the older stale fake-native `DedicatedServer64` contract |
| sevendaystodie | SteamCMD — PASSED 2026-05-29; readiness follows the real `output_log__*.txt` surface and A2S answers on the managed game port. The current runtime contract additionally claims and publishes the complete base TCP+UDP plus `port + 1..3` UDP set for both process and Docker. The 2026-07-16 Docker setup hit app `294420`'s known repeated bare SteamCMD state `0x202`; the shared setup helper now preserves the explicit app id so the existing evidence-backed transient classifier applies consistently. Replacement CI validation is pending. |
| sniperelite4server | Docker runtime (Wine/Proton) — PASSED 2026-05-30; anonymous SteamCMD app `568880` installs the Windows payload and AlphaGSM stages install-root `default.cfg`. The current branch replaces the stale queryport/TCP assumption with the shipped config's game UDP, auth UDP, update UDP, and lobby TCP layout plus generic UDP health on the game port; process launches use Proton under Xvfb and replacement CI validation is pending. |
| soulmask | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on the validated Linux Docker-backed `wine-proton` lane once AlphaGSM launches the real Windows dedicated depot through root `WSServer.exe`, treats the live health surface as generic `tcp` on the managed main port instead of the older stale A2S assumption, and proves `query`, `info`, `info --json`, plus clean shutdown on the current server contract |
| sonsoftheforestserver | Docker runtime (Wine/Proton) — PASSED 2026-05-29; AlphaGSM writes the managed JSON `user-data/dedicatedserver.cfg`, seeds `ownerswhitelist.txt`, starts Xvfb from the shared container entrypoint, and validates A2S on the managed `queryport`. CI now routes one Docker-default heavy lifecycle instead of duplicating the currently failing forced host-process Wine lane. |
| solserver | SteamCMD |
| subsistenceserver | Docker runtime (Wine/Proton) — PASSED 2026-06-03; fresh focused integration plus smoke now prove the earlier DirectX-only disabled note was stale. Anonymous SteamCMD setup for app `1362640` installs the full Windows dedicated payload, AlphaGSM launches the upstream `Binaries/Win64/UDK.exe` dedicated host inside the shared `wine-proton` runtime, hands Docker the bare Windows command so the shared entrypoint can seed the Wine prefix and Xvfb correctly, syncs the real UDK config layer so the managed `queryport` becomes authoritative before start, and validates `query`, `info`, and `info --json` over A2S on the managed query port |
| squad44server | SteamCMD |
| squadserver | SteamCMD |
| stationeersserver | SteamCMD — PASSED 2026-05-29; smoke and focused integration now both pass on the post-September-2025 Linux dedicated-server contract (`rocketstation_DedicatedServer.x86_64 -file start ... -logFile ./server.log -settings ... UseSteamP2P false LocalIpAddress 0.0.0.0`), with the shared setup port-retry helper covering the colliding default `updateport` and generic `udp` `query` / `info` on the managed game port |
| starruptureserver | Docker runtime (Wine/Proton) — PASSED 2026-06-01; fresh focused integration plus follow-up smoke validation now prove the old timeout-only skip was stale: anonymous SteamCMD setup for app `3809400` installs the real Windows dedicated payload, AlphaGSM launches `StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe` inside the shared `wine-proton` runtime, stages root `DSSettings.txt` from the checked-in template before launch, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed main game port |
| stnserver | SteamCMD |
| svenserver | SteamCMD (GoldSrc) |
| terraria_tshock | Direct download — PASSED 2026-05-28; smoke and focused integration both pass on the Docker-backed lifecycle once the shared `steamcmd-linux` runtime image includes the required `.NET` runtimes, and CI now builds that image from the branch before validation |
| terraria_vanilla | Direct download |
| terratechworldsserver | Wine/Proton — PASSED 2026-05-28; the Linux lane now launches `TT2/Binaries/Win64/TT2Server-Win64-Shipping.exe` directly under `xvfb-run` + Wine, syncs AlphaGSM's managed port into `dedicated_server_config.json`, reaches `Created socket for bind address`, `IpNetDriver listening on port`, and `Bringing World` in `TT2/Saved/Logs/TT2.log`, and passes the full AlphaGSM lifecycle on the generic `udp` contract instead of A2S |
| tf2 | SteamCMD (Source) |
| tfcserver | SteamCMD (GoldSrc) |
| thefrontserver | SteamCMD — PASSED on the Ubuntu 24.04 baseline; process and Docker retain one game command. The current Docker correction opts into the shared non-root host UID/GID contract with manager-owned HOME state, fail-closed host-path translation, and matching `doctor` checks. Replacement CI validation is pending and this does not record a new pass. |
| trackmaniaserver | Direct download — PASSED 2026-05-17; setup now syncs the configured XML-RPC port into `GameData/Config/dedicated_cfg.txt`, launch stays attached with `/nodaemon`, and query/info use TCP reachability on the XML-RPC endpoint |
| unturned | SteamCMD |
| ut2k4server | Direct download — PASSED 2026-05-29; fresh focused integration now passes once AlphaGSM requires the OldUnreal installer prerequisites, isolates the runtime `HOME` under `.alphagsm/ut2k4-home` so per-instance user state no longer leaks between servers, extends the setup budget for the full native installer path, and aligns `query`, `info`, and `info --json` to the current generic `udp` health surface on the managed game port |
| ut99server | Direct download |
| valheim | Docker runtime (SteamCMD Linux) — PASSED; the current contract includes `libatomic1`, `libpulse0`, and `libpulse-dev`, waits for `Game server connected`, publishes the primary and adjacent UDP server ports, and validates generic UDP `query`, `info`, and `info --json` on the primary game port instead of requiring a stale A2S response. Fresh validation is pending the replacement CI run. |
| veinserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration now proves the old timeout-only disable note was stale: anonymous SteamCMD setup for app `2131400` completes on the validated native Linux lane, AlphaGSM launches `VeinServer.sh` inside the shared `steamcmd-linux` runtime as a non-root user with the host SteamCMD `steamclient.so` bootstrap mounted into `~/.steam/sdk64`, and the live health surface is generic `tcp` on the managed main game port rather than the older stale timeout-only assumption |
| vintagestoryserver | Direct download / Docker runtime — PASSED 2026-05-30; fresh focused integration now passes once validation follows the module's existing `steamcmd-linux` Docker runtime instead of requiring host `dotnet`, and the rerun is pinned to the rebuilt branch-local `alphagsm-steamcmd-linux-runtime:test` image so `dotnet VintagestoryServer.dll --dataPath <install_dir>` resolves cleanly inside the container and AlphaGSM proves `query`, `info`, `info --json`, `status`, and `stop` on the managed generic `tcp` game port |
| warbandserver | Direct download (Wine) — PASSED 2026-05-18; the module now uses the official `mb_warband_dedicated_1174.zip` archive directly instead of scraping the Cloudflare-blocked TaleWorlds page, syncs `Sample_Battle.txt` to the configured AlphaGSM port/maxplayers, runs the nested `mb_warband_dedicated.exe` through Wine/Proton plus `xvfb-run` on headless Linux, and smoke/integration wait on `info --json` protocol `tcp` instead of stale screen-log markers |
| wreckfestserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh smoke and focused integration now prove the old missing-Linux-binary disabled note was stale: anonymous SteamCMD setup for app `361580` installs the real Windows dedicated payload, AlphaGSM launches the shipped `Wreckfest_x64.exe` under the shared `wine-proton` runtime, seeds `server_config.cfg` from the vendor `initial_server_config.cfg`, syncs `game_port` / `query_port` / `steam_port` plus managed server identity settings, and validates `query`, `info`, and `info --json` on the current generic `tcp` health surface at the managed main game port instead of the older fake native-Linux / A2S contract |
| wfserver | SteamCMD — PASSED; smoke plus process and Docker integration use AlphaGSM's live Quake `info --json` response on the managed UDP game port for readiness because Docker console logs can omit the traditional startup markers |
| wurmserver | SteamCMD |
| xntserver | Direct download / Docker runtime — PASSED 2026-05-30; AlphaGSM launches Xonotic through the upstream `server/server_linux.sh` wrapper from the detected archive content root, maps that nested root to the matching Docker working directory, writes managed `server.cfg`, and spaces runtime-resolved Quake checks around DarkPlaces' rate limit. CI now keeps one Docker-default lifecycle; replacement validation of the restored wrapper contract is pending. |
| battlecryoffreedomserver | SteamCMD (Wine/Proton) — PASSED; Linux launches use Xvfb and `query`, `info`, plus `info --json` use the validated TCP health surface on the managed game port |
| ckserver | SteamCMD |
| enshrouded | Docker runtime (Wine/Proton) — PASSED; AlphaGSM now treats `enshrouded_server.json` as authoritative, syncs `name` and `queryPort`, preserves unrelated generated settings, and defaults `queryPort` to the managed port `15637` rather than the stale `port + 1` value. The 2026-07-16 bulk process lane completed query/info but left the Wine child answering after its `screen` session was killed; because Enshrouded had been explicitly Docker-validated rather than process-validated, CI now keeps one Docker-default heavy lifecycle. Replacement CI validation is pending. |
| groundbranchserver | SteamCMD (Proton) — replacement CI validation pending; smoke and integration require the real `GameNetDriver` ready marker before checking AlphaGSM's generic UDP game-port health surface because the current SteamSockets build does not expose local A2S on `QueryPort` |
| mythofempiresserver | Docker runtime (Wine/Proton) — PASSED; the current branch keeps the module's A2S query contract runtime-agnostic, resolves the Docker-reachable host, and replaces the host-only `MOE.log` readiness wait with AlphaGSM `info --json` on `queryport`. CI now runs this large install as one Docker-default heavy lifecycle; replacement validation is pending. |
| reignofdwarfserver | Docker runtime (Wine/Proton) — PASSED; the live payload exposes generic TCP on the managed game port rather than A2S on `queryport`, so CI waits for AlphaGSM's TCP `info --json` surface. The forced host-Proton process exited during the 2026-07-16 full run, so CI keeps one Docker-default lifecycle. |
| sunkenlandserver | SteamCMD (Wine/Proton) — PASSED; Linux launches use Xvfb and `query`, `info`, plus `info --json` use the validated TCP health surface on the managed game port |
| theforestserver | SteamCMD (Wine/Proton) — PASSED; AlphaGSM writes the native `server-data/Server.cfg`, keeps saves under `server-data/saves`, launches the Windows Unity server under Xvfb with the required config/save path arguments, claims and publishes the managed game, query, and Steam communication ports, and validates A2S on `queryport` |
| askaserver | SteamCMD (Wine) |
| blackops3server | Docker runtime (Wine/Proton) — PASSED; the current branch follows the shipped unranked server launch shape without the ineffective custom `-port` switch, maps the managed three-port group to fixed container ports `27015..27017`, and combines `CreateDedicatedModsLobby: ready!` with AlphaGSM generic UDP query/info. The 2026-07-16 server reached readiness and answered AlphaGSM's UDP probe; the stale test assertion expecting A2S wording now matches the declared generic UDP output. CI runs one Docker-default heavy lifecycle; replacement validation is pending. |
| pixarkserver | SteamCMD (Wine) |
| remnantsserver | Docker runtime (Wine/Proton) — PASSED; AlphaGSM launches `RemSurvivalServer.exe` and validates generic TCP health on the managed game port because the current payload did not answer A2S on `queryport`. The forced process lane exited during the 2026-07-16 run, so CI now keeps one Docker-default lifecycle and no longer requires the install-tree log before AlphaGSM readiness. Both process and Docker contracts now explicitly select Proton. |
| readyornotserver | Docker runtime (Wine/Proton) — PASSED 2026-03-28; the current EOS-backed dedicated tool remains supervised in Docker but no longer answers the stale A2S contract in the 2026-07-16 run. Smoke/integration now require `ReadyOrNot.log` engine readiness and use generic `udp` query/info on the managed game port; replacement CI validation is pending. |
| returntomoriaserver | Docker runtime (Wine/Proton) — PASSED 2026-05-29; AlphaGSM manages `MoriaServerConfig.ini`, retains the interactive console required by world startup, waits for the game-owned `Status.json` running state without retaining invite/join secrets, then validates exact generic `udp` readiness through `info --json`. The console FIFO now invokes the Wine/Proton image entrypoint before `MoriaServer.exe`, preventing the prior native exec-format exit. Replacement validation is pending. |
| rs2server | Docker runtime (Wine/Proton) — PASSED 2026-07-16; the current Docker lifecycle completed in 4:08 and proved `query`, `info`, `info --json`, and shutdown verification on the module-owned A2S `queryport`. The matching forced host-process Wine lane stalled for 20 minutes without reaching A2S, so CI now keeps RS2 as one Docker-default heavy lifecycle. |
| rwserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh smoke and focused integration now prove the old disabled Java-era note was stale: anonymous SteamCMD setup for app `339010` installs the current native Linux dedicated server, AlphaGSM launches `RisingWorldServer.x64` with the required `LD_LIBRARY_PATH` bootstrap inside the shared `steamcmd-linux` runtime as a non-root user, syncs `Server_Port` / `Server_Name` / `World_Name` into `server.properties`, and validates `query`, `info`, and `info --json` on Rising World's real TCP web-query surface at `serverport - 1` |
| insserver | Smoke re-enabled: PASSED 2026-03-28; process, Docker, and smoke readiness uses AlphaGSM's real A2S `info --json` response because Docker console logs can omit the traditional Source startup markers |
| inssserver | Smoke re-enabled: PASSED 2026-03-28; smoke now waits for startup markers and `info --json` protocol `a2s` on the Sandstorm query path |
| ts3server | Smoke re-enabled: Direct download — PASSED 2026-03-28; smoke now waits for `ServerQuery created` and `info --json` protocol `ts3` |

## ENABLED (AUTH) (48)

These supported rows require provider-managed authentication, credentials,
tokens, licenses, or provisioning before setup/start can fully succeed.

| Test | Type |
|------|------|
| gtafivemserver | txAdmin/server-data provisioning plus Cfx license key |
| arma2coserver | authenticated Steam/SteamCMD entitlement for Arma 2: Combined Operations dedicated server app `33935` |
| arma3server | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3altislifeserver | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3desolationreduxserver | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3epochserver | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3exileserver | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3headlessserver | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3wastelandserver | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3_altislife | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3_desolationredux | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3_epoch | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3_exile | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3_headless | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3_vanilla | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| arma3_wasteland | authenticated Steam/SteamCMD entitlement for Arma 3 dedicated server app `233780` |
| dayzarma2epochserver | authenticated Steam/SteamCMD entitlement for Arma 2: Combined Operations dedicated server app `33935` |
| dayzserver | authenticated Steam/SteamCMD entitlement for DayZ dedicated server app `223350` |
| ducksideserver | authenticated Steam/SteamCMD entitlement for Duckside dedicated server app `2690320` |
| hellletlooseserver | authenticated Steam/SteamCMD entitlement for Hell Let Loose dedicated server app `822500` |
| motortownserver | authenticated Steam/SteamCMD entitlement for Motor Town dedicated server app `2223650` |
| reignofkingsserver | authenticated Steam/SteamCMD entitlement for Reign of Kings dedicated server app `381690` |
| ror2server | authenticated Steam/SteamCMD entitlement for Risk of Rain 2 dedicated server app `1180760` |
| staxelserver | authenticated Steam/SteamCMD entitlement for Staxel dedicated server app `755170` |
| brickadiaserver | authenticated Steam/SteamCMD entitlement for Brickadia dedicated server app `3017590` |
| interstellarriftserver | authenticated Steam/SteamCMD entitlement for Interstellar Rift dedicated server app `363360` |
| twserver | authenticated Steam/SteamCMD entitlement for server app `380840` |
| acserver | authenticated SteamCMD entitlement for Assetto Corsa dedicated server app `302550`; the Windows depot also contains the native Linux server |
| accserver | authenticated Steam/SteamCMD entitlement for Assetto Corsa Competizione dedicated server app `1430110` |
| boserver | authenticated Steam/SteamCMD entitlement for Blackwake: Overgrowth dedicated server app `416881` |
| deadmatterserver | authenticated Steam/SteamCMD entitlement for Dead Matter dedicated server app `1110990` |
| kfserver | authenticated Steam/SteamCMD entitlement for Killing Floor dedicated server app `215360` |
| mw3server | authenticated Steam/SteamCMD entitlement for Modern Warfare 3 dedicated server app `115310` |
| police1013server | authenticated Steam/SteamCMD entitlement for Police 1013 dedicated server app `2691380` |
| pcars2server | authenticated Steam/SteamCMD entitlement for Project CARS 2 dedicated server app `413770` |
| roserver | authenticated Steam/SteamCMD entitlement for Red Orchestra dedicated server app `223250` |
| bannerlordserver | authenticated Steam/SteamCMD access to Bannerlord dedicated server app `1863440` branch `linux_test`, plus a TaleWorlds custom server token before start |
| chivalryserver | authenticated Steam/SteamCMD entitlement for Chivalry: Medieval Warfare Dedicated Server app `220070` |
| brokeprotocolserver | authenticated Steam/SteamCMD entitlement for BROKE PROTOCOL app `696370` |
| bsserver | authenticated Steam or SteamCMD entitlement for Blade Symphony dedicated server app `228780` plus the shared owned `berimbau` depot content that can be missing from anonymous installs |
| dabserver | authenticated Steam or SteamCMD entitlement for current Double Action: Boogaloo app `317360` content; the retired dedicated tool app `317800` still crashes on modern Linux and anonymous SteamCMD for `317360` returns `No subscription` |
| dysserver | authenticated Steam or SteamCMD access to Dystopia Beta Dedicated Server app `17595` on the historical `Previous` beta path |
| pathoftitansserver | Alderon host account token for managed installs, or staged archive override |
| redmserver | txAdmin/server-data provisioning plus Cfx license key |
| battlebitserver | BattleBit community-server provisioning/approval plus a reachable `apiendpoint` (optional `apitoken`) |
| tiserver | EOS dedicated-server client ID/secret for Epic Online Services authentication |
| iosserver | authenticated Steam/SteamCMD access to IOSoccer Dedicated Server app `673990` branch `iosoccer2025` or `beta`; anonymous SteamCMD fails to set those sdk2013 branches and the public branch still crashes on Linux |
| zpsserver | authenticated Steam client session alongside Zombie Panic! Dedicated Server app `4523420`; even with the SteamDB-advertised `-steam -secure` launch flags, HLDS still reports `SteamAPI_IsSteamRunning()` missing under the anonymous Docker lane |

## ENABLED (BYO) (45)

These supported rows are intentionally explicit about the blocker class:
owned assets, exported client files, external services, or direct archive
URLs.

| Test | Type |
|------|------|
| astroneerserver | Docker runtime (Wine/Proton); provide an externally routable IPv4 endpoint through `ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP` for registration validation. The lifecycle remains Docker-first and is explicitly skipped in CI when that external prerequisite is absent. |
| aloftserver | owned Aloft server tree |
| ahlserver | owned Action Half-Life mod content tree |
| alienarenaserver | staged native Alien Arena dedicated server tree |
| atsserver | owned exported client packages/settings |
| atlasserver | staged `ServerGrid.json`, `ServerGrid.ServerOnly.json`, and `ServerGrid/` export under `ShooterGame/` |
| bf1942server | direct archive URL or staged Battlefield 1942 Linux dedicated server tree |
| bbserver | owned BrainBread mod content tree |
| bfvserver | direct archive URL or staged Battlefield Vietnam Linux dedicated server tree |
| cod2server | owned localized base-game assets |
| cod4server | owned base-game assets |
| codserver | owned multiplayer map content; the public dedicated archive ships the server payload and base PK3 files but no `maps/mp/*.bsp` map data |
| coduoserver | owned base multiplayer assets |
| dstserver | cluster token plus staged cluster config |
| etlegacyserver | owned base-game assets |
| ets2server | owned exported client packages/settings |
| foundryserver | staged native FOUNDRY dedicated server tree |
| goldeneyesourceserver | complete operator-staged Source 2007/AppID 310 base plus preserved top-level `gesource` content; the official `/go/` path returns a 241-byte HTML meta-refresh in process and Docker CI, the authoritative ModDB release returns HTTP 403, and the signed official object returns HTTP 401, so AlphaGSM does not claim a network install or a current pass |
| gravserver | owned GRAV dedicated server tree |
| hogwarpserver | archive URL or staged Windows server tree |
| identityserver | archive URL or staged Identity server tree |
| jk2server | direct archive URL or staged Jedi Outcast Linux dedicated server tree |
| minecraft_custom | user-supplied server jar; setup seeds managed properties plus the accepted-EULA file without launching the BYO jar |
| minecraft_tekkit | direct Tekkit archive URL or staged Tekkit.jar |
| mxbikesserver | user-supplied dedicated archive URL |
| ndserver | staged Nuclear Dawn content tree |
| nsserver | owned Natural Selection mod content tree |
| q3server | owned base-game assets |
| q4server | direct archive URL or staged Quake 4 Linux dedicated server tree |
| qlserver | authenticated entitlement plus server auth/config |
| rtcwserver | owned base-game assets |
| sampserver | direct archive URL or staged SA-MP Linux dedicated server tree |
| sfcserver | official SourceForts Classic ModDB full-version tree staged under `sfclassic/` |
| skyrimtogetherrebornserver | direct archive URL or staged Skyrim Together Reborn server tree |
| ss14server | direct Linux x64 server archive while the official Wizard's Den build feed publishes no server builds; the managed `server_config.toml`, `robust_status`, process runtime, and Docker runtime lifecycle remain supported when an archive is supplied |
| mohaaserver | owned MOHAA dedicated server tree |
| sof2server | owned SOF2 dedicated server tree |
| stormworksserver | authenticated Steam/SteamCMD access to install the Dedicated Server tool, then a staged installed server tree |
| starbound | staged native Starbound server tree |
| subnauticaserver | owned client installation path |
| tsserver | owned The Specialists mod content tree |
| ut3server | owned UT3 dedicated server tree; optional OpenSpy credentials for advertising |
| vsserver | owned Vampire Slayer mod content tree |
| lifeisfeudalserver | local MySQL/MariaDB service on `localhost` |
| zmrserver | staged Zombie Master: Reborn content tree |

## DISABLED (3)

| Test | Reason |
|------|--------|
| abfserver | Windows-only SteamCMD app 2857200 is now staged with the forced-Windows payload and shared Wine/Proton runtime; remains disabled pending fresh GitHub Docker lifecycle validation. |
| bobserver | Prior CI runs timed out while downloading SteamCMD app 882430; the integration test now allows 30 minutes, uses the documented `LinuxServer/BeastsOfBermudaServer.sh` launcher path and arguments, and no longer permanently skips the failure, but the module remains disabled pending fresh GitHub CI validation. |
| counterstrikeglobaloffensive | SteamCMD app 740 installs legacy CS:GO build 1575; server reaches Steam, receives MasterRequestRestart, and self-shuts down while hibernating. Official CS2 dedicated servers were merged into app 730. |

## SKIPPED (0)

Tests with `pytest.mark.skip` or "a `require_proton()` / `require_command()` guard — need a prerequisite before they can run.

All integration tests have been tested and categorized. No untested servers remain.
