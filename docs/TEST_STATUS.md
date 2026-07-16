# Integration Test Status

Last updated: 2026-07-16

## Summary

Tracker note: on 2026-06-27 the live support gate files were reconciled with the
documented `ENABLED (AUTH)` / `ENABLED (BYO)` rows and CI now validates that
`docs/TEST_STATUS.md`, `disabled_servers.conf`, `enabled_byo_servers.conf`, and
`enabled_auth_servers.conf` stay in sync.

| Status   | Count |
|----------|-------|
| PASSED   | 146      |
| ENABLED (AUTH) | 47 |
| ENABLED (BYO) | 41 |
| DISABLED | 3      |
| SKIPPED  | 0      |

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **ENABLED (AUTH)** — Supported server module that still requires provider-managed authentication, credentials, tokens, licenses, or provisioning before setup/start can fully succeed.
- **ENABLED (BYO)** — Supported server module that still requires an explicit operator-provided prerequisite such as owned assets, exported client files, an external service, or a direct URL.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.

## Counter-Strike Split

- `counterstrike2` and `cs2server` are the current CS2 surface. They now have a dedicated integration test and smoke runner, and they are not listed in `disabled_servers.conf`.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by Steam app `740` and are disabled.

## PASSED (146)

| Test | Type |
|------|------|
| acserver | SteamCMD |
| ahl2server | SteamCMD (Source) |
| argoserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; anonymous SteamCMD setup for app `563930` selects the upstream `server` beta required for the native Linux dedicated payload, AlphaGSM launches the shipped `argoserver` binary inside the shared `steamcmd-linux` runtime, syncs `server.cfg` from the managed `servername`, and validates `query`, `info`, and `info --json` on Argo's current generic `tcp` health surface at the managed main game port |
| ark | Docker runtime (SteamCMD Linux) — PASSED 2026-06-01; fresh formal integration now proves the old size-based disabled note is no longer the real blocker: anonymous SteamCMD setup for app `376030` completes on the shared `steamcmd-linux` runtime, AlphaGSM launches `ShooterGame/Binaries/Linux/ShooterGameServer` from its real working directory inside the Docker lane as a non-root user with the shared Steam bootstrap mounted into `~/.steam/sdk64/steamclient.so`, and validates real A2S `query`, `info`, and `info --json` on the managed `queryport` instead of the older stale host-process / generic-TCP assumptions |
| arksurvivalascended | Docker runtime (Wine/Proton) — PASSED 2026-05-30; fresh smoke and integration now both pass on the branch-local `wine-proton` runtime image with anonymous SteamCMD install for app `2430930`, and the validated Linux health surface is generic `tcp` on the managed main game port instead of the older stale log-marker and A2S assumptions |
| armarserver | SteamCMD |
| astroneerserver | Docker runtime (Wine/Proton) — PASSED 2026-05-29; fresh smoke and integration now both pass on the branch-local `wine-proton` runtime image once AlphaGSM routes Astroneer's Docker lane through the shared in-container Xvfb entrypoint so UE4 prerequisite bootstrap no longer aborts with `Failed to create window`, and `query`, `info`, and `info --json` are aligned to the real generic `tcp` status surface on the managed main port instead of the older stale A2S expectation |
| avserver | SteamCMD |
| archive_backed_installs | Archive |
| bb2server | SteamCMD (Source) |
| btlserver | SteamCMD |
| btserver | SteamCMD |
| bdserver | SteamCMD (GoldSrc) |
| bmdmserver | SteamCMD (Source) |
| blackwakeserver | Docker runtime (Wine/Proton) — PASSED 2026-05-30; fresh focused integration now passes on the Docker-backed Linux `wine-proton` lane once AlphaGSM treats the validated runtime contract honestly: `query`, `info`, and `info --json` use the stable generic `tcp` surface on the managed main port instead of the older stale A2S-on-`queryport` assumption, while `stop` routes through the shared runtime layer rather than a direct `screen` console call |
| ccserver | SteamCMD (Source) |
| citadelserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disabled note was stale: anonymous SteamCMD setup for app `489650` installs the real native Linux dedicated payload, AlphaGSM launches the shipped `CitadelServer.sh` wrapper or falls back to the nested `Citadel/Binaries/Linux/CitadelServer-Linux-Shipping` binary, mounts the shared Steam bootstrap into `~/.steam/sdk64/steamclient.so`, and validates `query`, `info`, and `info --json` on Citadel's real generic `tcp` health surface at the managed main game port rather than the older stale `queryport` A2S assumption |
| colserver | SteamCMD |
| conanexiles | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh smoke, formal integration, and direct shipping-exe probe now all prove the old missing-Linux-binary row was stale. Anonymous SteamCMD app `443030` installs a real Windows dedicated payload, AlphaGSM launches `ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe` inside the shared `wine-proton` runtime, syncs `Engine.ini` / `Game.ini` under `ConanSandbox/Saved/Config/WindowsServer/`, and validates real A2S `query`, `info`, and `info --json` on the managed `queryport` instead of the old fake native-Linux contract |
| counterstrike2 | SteamCMD (Source 2) — PASSED 2026-04-08 |
| csczserver | SteamCMD (GoldSrc) |
| csserver | SteamCMD (GoldSrc) |
| cssserver | SteamCMD (Source) |
| craftopiaserver | SteamCMD |
| cryofallserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale: anonymous SteamCMD setup for app `1061710` installs a real native `.NET 6` dedicated server payload, AlphaGSM stages `Data/SettingsServer.xml` from a managed template, launches `dotnet Binaries/Server/CryoFall_Server.dll loadOrNew` inside the shared `steamcmd-linux` runtime, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed main game port |
| dayofdragonsserver | SteamCMD |
| darkandlightserver | Docker runtime (Wine/Proton) — PASSED 2026-05-30; fresh smoke and integration now both pass on the branch-local `wine-proton` runtime image once AlphaGSM treats the validated Linux contract honestly: Dark and Light answers `query`, `info`, and `info --json` on the managed main game port as generic `udp`, stop flows through the shared runtime layer, and the Docker-backed Xvfb/software-GL lane no longer depends on a live host `screen` session or the older stale `queryport` A2S assumption |
| deadpolyserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh focused integration now proves the old missing-binary disable note was stale in a narrower way: anonymous SteamCMD setup for app `2208380` installs the real Windows dedicated payload, AlphaGSM stages `DeadPoly/Saved/Config` from the shipped `1 RENAME Config` tree, launches `DeadPolyServer.exe -log -nosteam` under the shared Wine/Proton runtime, and validates `query`, `info`, and `info --json` on the current generic `tcp` health surface at the managed `queryport` |
| dmcserver | SteamCMD (GoldSrc) |
| dodserver | SteamCMD (GoldSrc) |
| dodsserver | SteamCMD (Source) |
| doiserver | SteamCMD (Source) |
| ecoserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-29; fresh smoke and integration now both pass on the branch-local `steamcmd-linux` runtime image once AlphaGSM launches Eco in offline mode, seeds `.steam/sdk64/steamclient.so` plus `steam_appid.txt` inside the install tree, stages a writable `.net-bundle-cache`, syncs `Configs/Network.eco` side ports from the managed base port, and aligns `query`, `info`, and `info --json` to Eco's real generic `tcp` surface on the managed main port |
| emserver | SteamCMD (Source) — PASSED 2026-05-23; focused integration now reaches real Source log readiness, hibernation-safe `info --json`, A2S query/info, and clean shutdown on the anonymous SteamCMD install path |
| empyrionserver | Wine/Proton — PASSED 2026-05-29; the direct `DedicatedServer/EmpyrionDedicated.exe` Linux contract now syncs `dedicated.yaml` `Srv_Port`, reads readiness from `Logs/alphagsm-dedicated.log`, and proves `query`, `info`, `info --json`, and clean shutdown on Empyrion's live STCP TCP listener at `port + 3` instead of the older stale fixed-`30004` / A2S assumption |
| exfilserver | SteamCMD |
| fearthenightserver | Wine/Proton — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the Linux/Proton lane once AlphaGSM syncs `Moonlight/Saved/Config/WindowsServer/Engine.ini` and `GameUserSettings.ini`, launches the dedicated server with the real `Pittsburgh_Overworld?listen?Port=...?QueryPort=...?SessionName=...?MaxPlayers=...` map URL instead of the older stale bare-map contract, and treats the live health surface as generic `udp` on the managed game port because the current Linux runtime still does not expose a working A2S listener on `queryport` |
| fofserver | SteamCMD (Source) |
| frozenflameserver | SteamCMD |
| gmodserver | SteamCMD (Source) |
| goldeneyesourceserver | Direct download |
| hl2dmserver | SteamCMD (Source) |
| hldmserver | SteamCMD (GoldSrc) |
| hldmsserver | SteamCMD (Source) |
| heatserver | Wine/Proton — PASSED 2026-05-29; a fresh SteamCMD-managed lifecycle now passes on `release_v1` after AlphaGSM bootstraps missing `Configuration/ServerSettings.cfg` on first launch, syncs `portNumber` / `steamAuthPort` / `maxPlayers` / `levelName` into the native config, reads readiness from `Logs/Console*.txt`, and proves A2S `query`, `info`, `info --json`, and clean shutdown on the managed `queryport` |
| hurtworldserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale: anonymous SteamCMD setup for app `405100` installs the real native Linux dedicated payload, AlphaGSM prefers `Hurtworld.x86_64` while falling back to the shipped Linux executables, launches the real headless `-exec "host ...;queryport ...;maxplayers ...;servername ..."` contract inside the shared `steamcmd-linux` runtime, and validates A2S `query`, `info`, and `info --json` on the managed `queryport` |
| hzserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale in a narrower way: anonymous SteamCMD setup for app `2728330` installs a Windows-only dedicated payload, AlphaGSM launches the real `HumanitZServer-Win64-Shipping.exe` binary inside the shared `wine-proton` runtime, mirrors `ServerName` and `MaxPlayers` into `HumanitZServer/GameServerSettings.ini` from the shipped reference config, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed `queryport` instead of the older stale Linux-binary assumption |
| icarusserver | Docker runtime (Wine/Proton) — PASSED 2026-05-30; fresh integration and smoke now both pass on the branch-local `wine-proton` runtime image once AlphaGSM treats the validated Linux contract honestly: anonymous SteamCMD setup for app `2089300` succeeds, the server stays up in the shared Docker-backed Xvfb/software-GL lane, and `query`, `info`, plus `info --json` all use the live generic `tcp` surface on the managed main port instead of the older stale log-marker and A2S assumptions |
| jc2server | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh smoke and focused integration now prove the old disabled missing-executable note was stale: anonymous SteamCMD setup for app `261140` installs the current native Linux dedicated server, AlphaGSM launches the real `Jcmp-Server` binary inside the shared `steamcmd-linux` runtime, seeds the required native `config.lua` from `default_config.lua`, stages the shipped `default_scripts/` into `scripts/`, and validates `query`, `info`, and `info --json` on JC2-MP's real generic `tcp` health surface at the managed main game port rather than the older stale CLI and A2S assumptions |
| jc3server | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh smoke and focused integration now prove the old disabled missing-executable note was stale: anonymous SteamCMD setup for app `619960` installs the current native Linux dedicated server, AlphaGSM launches the real `Server` binary inside the shared `steamcmd-linux` runtime as a non-root user with the host SteamCMD `steamclient.so` bootstrap mounted into `~/.steam/sdk64`, syncs the native `config.json` before start, and validates `query`, `info`, and `info --json` on JC3MP's real TCP health surface at `httpPort = port + 3` rather than the older stale CLI/A2S assumptions |
| kerbalspaceprogramserver | Docker runtime (SteamCMD Linux) — PASSED 2026-06-01; fresh smoke and focused integration now prove the old SteamCMD/platform skip note was stale: AlphaGSM downloads the Linux LunaMultiplayer release directly, launches the native `LMPServer-linux-x64/Server` host inside the shared `steamcmd-linux` runtime, creates first-run `Config/ConnectionSettings.xml` and `GeneralSettings.xml` when the upstream archive has not generated them yet, syncs the managed port, server name, and max players before start, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed main game port |
| kf2server | SteamCMD |
| l4dserver | SteamCMD (Source) |
| l4d2server | SteamCMD (Source) — PASSED 2026-06-01; fresh formal integration and smoke now prove app `222860` does support anonymous installs again when AlphaGSM stages the Windows depots first and then applies the Linux depots into the same server tree. The validated lifecycle uses the normal Source host-process lane, and `query`, `info`, plus `info --json` all answer via real A2S on the managed game port instead of the earlier stale `ENABLED (AUTH)` assumption. |
| lastoasisserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-30; fresh integration now proves the old timeout-only disable note was stale: anonymous SteamCMD setup for app `920720` completes, AlphaGSM launches the real native Linux binary `Mist/Binaries/Linux/MistServer-Linux-Shipping` inside the shared `steamcmd-linux` runtime as a non-root user, seeds `~/.steam/sdk64/steamclient.so` from the install-local Linux payload, and the validated health surface is generic `tcp` on the managed main game port rather than the older stale A2S `queryport` assumption |
| longvinterserver | Docker runtime — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the shared `steamcmd-linux` runtime image once AlphaGSM seeds `Longvinter/Saved/Config/LinuxServer/Game.ini` from the shipped `.default`, syncs `ServerName` / `MaxPlayers`, launches `LongvinterServer.sh` inside the container as the mounted server-directory owner instead of root, and treats the live health surface as generic `udp` on the managed game port instead of the older stale A2S `queryport` assumption |
| minecraft_bedrock | Docker runtime (service-console) — PASSED 2026-05-30; fresh focused integration now passes on the rebuilt branch-local `service-console` runtime image after AlphaGSM switches Bedrock setup from the stale JavaScript-page assumption to a direct browser-header archive fetch, keeps Docker-first lifecycle coverage on the shared runtime family, and uses Docker-stop for the container-backed stop path because Bedrock echoes console `stop` input without exiting cleanly under the shared exec-console path |
| minecraft_paper | Direct download |
| minecraft_bungeecord | Direct download — PASSED 2026-05-30; fresh focused integration now proves the tracker row was stale: AlphaGSM resolves the latest successful upstream BungeeCord Jenkins build automatically during `setup`, generates `config.yml`, and passes `query`, `info`, `info --json`, `status`, and clean shutdown on the managed SLP/TCP proxy port without requiring a bring-your-own jar URL |
| minecraft_vanilla | Direct download — PASSED 2026-05-16; the integration helper selects the newest release compatible with the installed Java runtime, and setup seeds managed properties plus the accepted-EULA file without leaving a bootstrap JVM alive before the real start lifecycle |
| minecraft_velocity | Direct download |
| minecraft_waterfall | Direct download |
| medievalengineersserver | Docker runtime (Wine/Proton) — PASSED 2026-06-03; fresh formal integration and smoke now prove the old immediate Proton-crash note was stale: anonymous SteamCMD setup for app `367970` completes, AlphaGSM stages `instance-data/MedievalEngineers-Dedicated.cfg`, launches `DedicatedServer64/MedievalEngineersDedicated.exe` inside the shared `wine-proton` runtime with the rebuilt Wine prefix bootstrap, and validates `query`, `info`, and `info --json` on the current generic `tcp` health surface at the managed main game port instead of the older stale A2S expectation. |
| memoriesofmarsserver | SteamCMD |
| miscreatedserver | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on the Docker-backed Linux `wine-proton` lane once AlphaGSM reads readiness from the real `user/server.log` surface and treats the live health surface as generic `tcp` on the managed main port instead of the older stale A2S-on-`port + 1` assumption |
| codserver | Docker runtime — PASSED 2026-05-23; standard integration/smoke now run through the shared `steamcmd-linux` Docker runtime image, which supplies the legacy `libstdc++.so.5` compatibility library required by the old Linux dedicated binary |
| codwawserver | Docker runtime — PASSED 2026-05-30; fresh focused integration now passes on the shared `steamcmd-linux` runtime image once AlphaGSM drives the archive-backed install through Docker and aligns `query`, `info`, and `info --json` to the current generic `tcp` health surface on the managed game port |
| mumbleserver | Docker runtime — PASSED 2026-05-18; standard integration/smoke now drive the module through the shared `simple-tcp` Docker runtime image because upstream does not publish an anonymous Linux server binary, while process mode still works when a host `mumble-server`/`murmurd` package is installed |
| mtaserver | Docker runtime — PASSED 2026-05-30; fresh focused integration and smoke now both pass on the branch-local `steamcmd-linux` runtime image once AlphaGSM auto-installs the official `baseconfig.tar.gz` payload, syncs `mods/deathmatch/mtaserver.conf` before launch, disables `ase` so no unmanaged `port + 123` listener is required, and aligns `query`, `info`, and `info --json` to MTA's real built-in HTTP listener on `httpport = port + 2` instead of the older stale ncurses/A2S assumptions |
| mordserver | SteamCMD |
| necserver | SteamCMD |
| nmrihserver | SteamCMD (Source) |
| noonesurvivedserver | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on the Docker-backed Linux `wine-proton` lane once AlphaGSM uses the shared Xvfb/software-GL container entrypoint and aligns `query`, `info`, and `info --json` to the current generic `tcp` status surface on the managed main port instead of the older stale A2S `queryport` expectation |
| notdserver | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on the Docker-backed Linux `wine-proton` lane once AlphaGSM mirrors `ServerSettings.ini` into `LF/Saved/Config`, adds the required `-DisableAntiCheat` Linux launch flag, and aligns `query`, `info`, and `info --json` to the current generic `tcp` status surface on the managed main port instead of the older stale A2S `queryport` expectation |
| nightingale | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh integration now proves the old timeout-only disable note was stale: anonymous SteamCMD setup for app `3796810` completes on the validated native Linux lane, AlphaGSM launches `NWXServer.sh` inside the shared `steamcmd-linux` runtime as a non-root user with the host SteamCMD `steamclient.so` bootstrap mounted into `~/.steam/sdk64`, and the live health surface is generic `tcp` on the managed main game port instead of the older stale host-log and A2S assumptions |
| ohdserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration and smoke now prove the old missing-binary disable note was stale: anonymous SteamCMD setup for app `950900` installs the real native Linux dedicated payload, AlphaGSM launches the shipped `HarshDoorstopServer.sh` wrapper or falls back to the nested `HarshDoorstop/Binaries/Linux/HarshDoorstopServer-Linux-Shipping` binary, mounts the shared Steam bootstrap into `~/.steam/sdk64/steamclient.so`, and validates A2S `query`, `info`, and `info --json` on the managed `queryport` instead of the older stale main-port / executable-name assumptions |
| opforserver | SteamCMD (GoldSrc) |
| outpostzeroserver | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on Linux/Proton once AlphaGSM mirrors the shipped `RunServer.bat` contract by launching `WindowsServer/SurvivalGameServer.exe RedPlanet ... -log`, syncing `Saved/Config/WindowsServer/Game.ini`, seeding `steam_appid.txt` beside the Win64 binaries, and waiting for the real post-load discovery surface before `query`, `info`, and `info --json` on generic `udp` at the managed game port |
| palworld | SteamCMD |
| primalcarnageextinctionserver | Wine/Proton — PASSED 2026-05-28; the corrected dedicated launch argv now feeds the `PC-Docks?...?bIsDedicated=true` map URL directly to `PrimalCarnageServer.exe`, focused smoke/integration reach `LoadMap: PC-Docks`, `Game class is 'PCTeamDeathMatchGame'`, and `NetMode is now 1`, A2S/info succeed on the managed `queryport`, and `stop` closes the live UE3 ports cleanly |
| pcarserver | PASSED 2026-05-23; standard smoke and focused integration now both pass, with readiness driven by `info --json` protocol `a2s` on the derived query port (`port + 1`) |
| projectzomboid | SteamCMD |
| q2server | Direct download — PASSED 2026-05-18; setup now builds Yamagi Quake II from source, stages the official demo `baseq2` data for anonymous installs, defaults fresh servers to `demo1`, and query/info use the dedicated Quake II `status` protocol |
| qwserver | Direct download — PASSED 2026-05-18; setup stages the public nQuake shareware, KTX runtime, configs, and core maps needed for anonymous MVDSV installs, GitHub CI authenticates release metadata resolution to avoid anonymous API rate limits, launch uses `-game ktx`, and query/info use the dedicated QuakeWorld `status` protocol |
| pvkiiserver | SteamCMD (Source) |
| pvrserver | Docker runtime — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the shared `steamcmd-linux` runtime image, and AlphaGSM `query`, `info`, and `info --json` correctly use Pavlov VR's helper UDP status port (`port + 400`) instead of the older stale A2S expectation |
| vrserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh smoke and focused integration now both prove the old missing-binary disabled note was stale: anonymous SteamCMD setup for app `1829350` installs the real Windows dedicated payload, AlphaGSM stages `Settings/ServerHostSettings.json` from the managed template, launches `VRisingServer.exe` under the shared Wine/Proton runtime with `-persistentDataPath`, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed `queryport` |
| ricochetserver | SteamCMD (GoldSrc) |
| rimworldtogetherserver | Direct download |
| rust | SteamCMD |
| satisfactory | SteamCMD |
| saleblazersserver | Wine/Proton — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the Linux/Wine dedicated path once AlphaGSM syncs `DedicatedServerConfig.json`, launches with the upstream `-config ./DedicatedServerConfig.json` contract under `xvfb-run` plus SDL `x11`/dummy audio/software GL, and treats the live helper surface as generic `udp` on `port + 1` instead of the older stale A2S `queryport` assumption |
| ss14server | Direct download — PASSED 2026-05-25; smoke and integration both reach the managed `server_config.toml` status surface, and `query` / `info --json` now pass through the live `robust_status` endpoint on the supported host-`dotnet` path |
| silicaserver | SteamCMD |
| scpslserver | SteamCMD |
| scumserver | Wine/Proton — PASSED 2026-06-02; fresh Docker-backed integration now proves the old timeout-only skip was stale: anonymous SteamCMD setup for app `3792580` installs the real Windows dedicated payload, AlphaGSM launches `SCUM/Binaries/Win64/SCUMServer.exe` under the shared `wine-proton` runtime, and the validated Linux health surface is generic `tcp` on the managed main game port instead of the older A2S/queryport assumption |
| smallandserver | SteamCMD |
| seserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh focused integration now proves the old missing-binary disable note was stale in a narrower way: anonymous SteamCMD setup for app `298740` installs the real Windows dedicated payload, AlphaGSM launches `DedicatedServer64/SpaceEngineersDedicated.exe` inside the shared `wine-proton` runtime from its required `DedicatedServer64` working directory, and validates `query`, `info`, and `info --json` on the current generic `udp` health surface at the managed main game port instead of the older stale fake-native `DedicatedServer64` contract |
| sevendaystodie | SteamCMD — PASSED 2026-05-29; fresh smoke and focused integration now both pass on the native Linux dedicated path once readiness follows the real `output_log__*.txt` surface instead of the stale screen log, the pre-start port refresh keeps the long SteamCMD setup from leaving a claimed stale port behind, and `query`, `info`, plus `info --json` are aligned to 7DTD's real A2S listener on the managed game port |
| sniperelite4server | Docker runtime (Wine/Proton) — PASSED 2026-05-30; fresh smoke and integration now both pass on the branch-local `wine-proton` runtime image with anonymous SteamCMD install for app `568880` once AlphaGSM stages an install-root `default.cfg` from the shipped example set, and the validated Linux health surface is generic `tcp` on the managed main game port instead of the older stale host-log and A2S assumptions |
| soulmask | Wine/Proton — PASSED 2026-05-29; fresh focused integration now passes on the validated Linux Docker-backed `wine-proton` lane once AlphaGSM launches the real Windows dedicated depot through root `WSServer.exe`, treats the live health surface as generic `tcp` on the managed main port instead of the older stale A2S assumption, and proves `query`, `info`, `info --json`, plus clean shutdown on the current server contract |
| sonsoftheforestserver | Docker runtime (Wine/Proton) — PASSED 2026-05-29; fresh smoke and integration now both pass on the branch-local `wine-proton` runtime image once AlphaGSM writes the managed JSON `user-data/dedicatedserver.cfg`, seeds `ownerswhitelist.txt` before first launch, starts Xvfb from the shared container entrypoint instead of a stuck in-container `xvfb-run` wrapper, and proves A2S `query`, `info`, `info --json`, plus clean shutdown on the managed `queryport` |
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
| thefrontserver | SteamCMD |
| trackmaniaserver | Direct download — PASSED 2026-05-17; setup now syncs the configured XML-RPC port into `GameData/Config/dedicated_cfg.txt`, launch stays attached with `/nodaemon`, and query/info use TCP reachability on the XML-RPC endpoint |
| unturned | SteamCMD |
| ut2k4server | Direct download — PASSED 2026-05-29; fresh focused integration now passes once AlphaGSM requires the OldUnreal installer prerequisites, isolates the runtime `HOME` under `.alphagsm/ut2k4-home` so per-instance user state no longer leaks between servers, extends the setup budget for the full native installer path, and aligns `query`, `info`, and `info --json` to the current generic `udp` health surface on the managed game port |
| ut99server | Direct download |
| valheim | SteamCMD |
| veinserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh focused integration now proves the old timeout-only disable note was stale: anonymous SteamCMD setup for app `2131400` completes on the validated native Linux lane, AlphaGSM launches `VeinServer.sh` inside the shared `steamcmd-linux` runtime as a non-root user with the host SteamCMD `steamclient.so` bootstrap mounted into `~/.steam/sdk64`, and the live health surface is generic `tcp` on the managed main game port rather than the older stale timeout-only assumption |
| vintagestoryserver | Direct download / Docker runtime — PASSED 2026-05-30; fresh focused integration now passes once validation follows the module's existing `steamcmd-linux` Docker runtime instead of requiring host `dotnet`, and the rerun is pinned to the rebuilt branch-local `alphagsm-steamcmd-linux-runtime:test` image so `dotnet VintagestoryServer.dll --dataPath <install_dir>` resolves cleanly inside the container and AlphaGSM proves `query`, `info`, `info --json`, `status`, and `stop` on the managed generic `tcp` game port |
| warbandserver | Direct download (Wine) — PASSED 2026-05-18; the module now uses the official `mb_warband_dedicated_1174.zip` archive directly instead of scraping the Cloudflare-blocked TaleWorlds page, syncs `Sample_Battle.txt` to the configured AlphaGSM port/maxplayers, runs the nested `mb_warband_dedicated.exe` through Wine/Proton plus `xvfb-run` on headless Linux, and smoke/integration wait on `info --json` protocol `tcp` instead of stale screen-log markers |
| wreckfestserver | Docker runtime (Wine/Proton) — PASSED 2026-05-31; fresh smoke and focused integration now prove the old missing-Linux-binary disabled note was stale: anonymous SteamCMD setup for app `361580` installs the real Windows dedicated payload, AlphaGSM launches the shipped `Wreckfest_x64.exe` under the shared `wine-proton` runtime, seeds `server_config.cfg` from the vendor `initial_server_config.cfg`, syncs `game_port` / `query_port` / `steam_port` plus managed server identity settings, and validates `query`, `info`, and `info --json` on the current generic `tcp` health surface at the managed main game port instead of the older fake native-Linux / A2S contract |
| wfserver | SteamCMD |
| wurmserver | SteamCMD |
| xntserver | Direct download / Docker runtime — PASSED 2026-05-30; fresh focused integration plus smoke now both pass on the shared `quake-linux` runtime once AlphaGSM launches Xonotic through the upstream `server/server_linux.sh` dedicated wrapper, writes the managed `server.cfg` into the install-root `data/` path the engine actually reads, and spaces the Quake `query`, `info`, and `info --json` checks around DarkPlaces' rate-limit window |
| battlecryoffreedomserver | SteamCMD (Proton) |
| ckserver | SteamCMD |
| enshrouded | SteamCMD (Proton) |
| groundbranchserver | SteamCMD (Proton) |
| mythofempiresserver | SteamCMD (Proton) |
| reignofdwarfserver | SteamCMD (Proton) |
| sunkenlandserver | SteamCMD (Proton) |
| theforestserver | SteamCMD (Proton) |
| askaserver | SteamCMD (Wine) |
| blackops3server | SteamCMD (Wine) |
| pixarkserver | SteamCMD (Wine) |
| remnantsserver | Re-enabled: server now launches `RemSurvivalServer.exe`, smoke and integration wait on `RemSurvival/Saved/Logs/RemSurvival.log` with a 600s startup budget, and `info --json` confirms protocol `a2s` |
| readyornotserver | Re-enabled: PASSED 2026-03-28; smoke now follows `ReadyOrNot/Saved/Logs/ReadyOrNot.log`, and integration now waits on the module-owned A2S `queryport` path instead of assuming `port + 1` |
| returntomoriaserver | Wine/Proton — PASSED 2026-05-29; fresh smoke and focused integration now both pass after AlphaGSM manages `MoriaServerConfig.ini` up front, keeps `Console.Enabled=true` for lifecycle control, syncs `ListenPort` plus the advertised host settings before first launch, and treats the live health surface as generic `udp` on the managed game port with readiness proven through `Moria/Saved/Config/Status.json` instead of the older stale wrapper-log / timeout assumptions |
| rs2server | Re-enabled: PASSED 2026-05-28; focused host integration now proves the full AlphaGSM lifecycle against the module-owned A2S `queryport`, including `query`, `info`, `info --json`, and shutdown verification after the shared setup port-retry helper and explicit smoke `queryport` wiring landed |
| rwserver | Docker runtime (SteamCMD Linux) — PASSED 2026-05-31; fresh smoke and focused integration now prove the old disabled Java-era note was stale: anonymous SteamCMD setup for app `339010` installs the current native Linux dedicated server, AlphaGSM launches `RisingWorldServer.x64` with the required `LD_LIBRARY_PATH` bootstrap inside the shared `steamcmd-linux` runtime as a non-root user, syncs `Server_Port` / `Server_Name` / `World_Name` into `server.properties`, and validates `query`, `info`, and `info --json` on Rising World's real TCP web-query surface at `serverport - 1` |
| insserver | Smoke re-enabled: PASSED 2026-03-28; smoke now waits for Source startup markers and `info --json` protocol `a2s` |
| inssserver | Smoke re-enabled: PASSED 2026-03-28; smoke now waits for startup markers and `info --json` protocol `a2s` on the Sandstorm query path |
| ts3server | Smoke re-enabled: Direct download — PASSED 2026-03-28; smoke now waits for `ServerQuery created` and `info --json` protocol `ts3` |

## ENABLED (AUTH) (47)

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

## ENABLED (BYO) (41)

These supported rows are intentionally explicit about the blocker class:
owned assets, exported client files, external services, or direct archive
URLs.

| Test | Type |
|------|------|
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
| coduoserver | owned base multiplayer assets |
| dstserver | cluster token plus staged cluster config |
| etlegacyserver | owned base-game assets |
| ets2server | owned exported client packages/settings |
| foundryserver | staged native FOUNDRY dedicated server tree |
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
