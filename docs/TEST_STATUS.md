# Integration Test Status

Last updated: 2026-05-29

## Summary

Tracker note: on 2026-05-15 the live `disabled_servers.conf` gate was reconciled
with already-supported Wine/Proton modules that were still blocked from `create`.
The status rows below already reflected those modules as active support surfaces;
this pass aligned the runtime gate with that existing tracker state.

| Status   | Count |
|----------|-------|
| PASSED   | 95      |
| DISABLED | 66      |
| SKIPPED  | 72      |

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.

## Counter-Strike Split

- `counterstrike2` and `cs2server` are the current CS2 surface. They now have a dedicated integration test and smoke runner, and they are not listed in `disabled_servers.conf`.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by Steam app `740` and are disabled.

## PASSED (95)

| Test | Type |
|------|------|
| acserver | SteamCMD |
| ahl2server | SteamCMD (Source) |
| armarserver | SteamCMD |
| avserver | SteamCMD |
| archive_backed_installs | Archive |
| bb2server | SteamCMD (Source) |
| btlserver | SteamCMD |
| btserver | SteamCMD |
| bdserver | SteamCMD (GoldSrc) |
| bmdmserver | SteamCMD (Source) |
| ccserver | SteamCMD (Source) |
| colserver | SteamCMD |
| counterstrike2 | SteamCMD (Source 2) — PASSED 2026-04-08 |
| csczserver | SteamCMD (GoldSrc) |
| csserver | SteamCMD (GoldSrc) |
| cssserver | SteamCMD (Source) |
| craftopiaserver | SteamCMD |
| dayofdragonsserver | SteamCMD |
| dmcserver | SteamCMD (GoldSrc) |
| dodserver | SteamCMD (GoldSrc) |
| dodsserver | SteamCMD (Source) |
| doiserver | SteamCMD (Source) |
| emserver | SteamCMD (Source) — PASSED 2026-05-23; focused integration now reaches real Source log readiness, hibernation-safe `info --json`, A2S query/info, and clean shutdown on the anonymous SteamCMD install path |
| exfilserver | SteamCMD |
| fofserver | SteamCMD (Source) |
| frozenflameserver | SteamCMD |
| gmodserver | SteamCMD (Source) |
| goldeneyesourceserver | Direct download |
| hl2dmserver | SteamCMD (Source) |
| hldmserver | SteamCMD (GoldSrc) |
| hldmsserver | SteamCMD (Source) |
| kf2server | SteamCMD |
| l4dserver | SteamCMD (Source) |
| minecraft_paper | Direct download |
| minecraft_vanilla | Direct download — PASSED 2026-05-16; local integration helper now selects the newest release compatible with the installed Java runtime |
| minecraft_velocity | Direct download |
| minecraft_waterfall | Direct download |
| memoriesofmarsserver | SteamCMD |
| codserver | Docker runtime — PASSED 2026-05-23; standard integration/smoke now run through the shared `steamcmd-linux` Docker runtime image, which supplies the legacy `libstdc++.so.5` compatibility library required by the old Linux dedicated binary |
| mumbleserver | Docker runtime — PASSED 2026-05-18; standard integration/smoke now drive the module through the shared `simple-tcp` Docker runtime image because upstream does not publish an anonymous Linux server binary, while process mode still works when a host `mumble-server`/`murmurd` package is installed |
| mordserver | SteamCMD |
| necserver | SteamCMD |
| nmrihserver | SteamCMD (Source) |
| opforserver | SteamCMD (GoldSrc) |
| palworld | SteamCMD |
| primalcarnageextinctionserver | Wine/Proton — PASSED 2026-05-28; the corrected dedicated launch argv now feeds the `PC-Docks?...?bIsDedicated=true` map URL directly to `PrimalCarnageServer.exe`, focused smoke/integration reach `LoadMap: PC-Docks`, `Game class is 'PCTeamDeathMatchGame'`, and `NetMode is now 1`, A2S/info succeed on the managed `queryport`, and `stop` closes the live UE3 ports cleanly |
| pcarserver | PASSED 2026-05-23; standard smoke and focused integration now both pass, with readiness driven by `info --json` protocol `a2s` on the derived query port (`port + 1`) |
| projectzomboid | SteamCMD |
| q2server | Direct download — PASSED 2026-05-18; setup now builds Yamagi Quake II from source, stages the official demo `baseq2` data for anonymous installs, defaults fresh servers to `demo1`, and query/info use the dedicated Quake II `status` protocol |
| qwserver | Direct download — PASSED 2026-05-18; setup now stages the public nQuake shareware, KTX runtime, configs, and core maps needed for anonymous MVDSV installs, launches with `-game ktx`, and query/info use the dedicated QuakeWorld `status` protocol |
| pvkiiserver | SteamCMD (Source) |
| ricochetserver | SteamCMD (GoldSrc) |
| rimworldtogetherserver | Direct download |
| rust | SteamCMD |
| satisfactory | SteamCMD |
| ss14server | Direct download — PASSED 2026-05-25; smoke and integration both reach the managed `server_config.toml` status surface, and `query` / `info --json` now pass through the live `robust_status` endpoint on the supported host-`dotnet` path |
| silicaserver | SteamCMD |
| scpslserver | SteamCMD |
| smallandserver | SteamCMD |
| solserver | SteamCMD |
| squad44server | SteamCMD |
| squadserver | SteamCMD |
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
| ut99server | Direct download |
| valheim | SteamCMD |
| warbandserver | Direct download (Wine) — PASSED 2026-05-18; the module now uses the official `mb_warband_dedicated_1174.zip` archive directly instead of scraping the Cloudflare-blocked TaleWorlds page, syncs `Sample_Battle.txt` to the configured AlphaGSM port/maxplayers, runs the nested `mb_warband_dedicated.exe` through Wine/Proton plus `xvfb-run` on headless Linux, and smoke/integration wait on `info --json` protocol `tcp` instead of stale screen-log markers |
| wfserver | SteamCMD |
| wurmserver | SteamCMD |
| xntserver | Direct download |
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
| rs2server | Re-enabled: PASSED 2026-05-28; focused host integration now proves the full AlphaGSM lifecycle against the module-owned A2S `queryport`, including `query`, `info`, `info --json`, and shutdown verification after the shared setup port-retry helper and explicit smoke `queryport` wiring landed |
| insserver | Smoke re-enabled: PASSED 2026-03-28; smoke now waits for Source startup markers and `info --json` protocol `a2s` |
| inssserver | Smoke re-enabled: PASSED 2026-03-28; smoke now waits for startup markers and `info --json` protocol `a2s` on the Sandstorm query path |
| ts3server | Smoke re-enabled: Direct download — PASSED 2026-03-28; smoke now waits for `ServerQuery created` and `info --json` protocol `ts3` |

## DISABLED (66)

| Test | Reason |
|------|--------|
| bsserver | Blade Symphony: 2006-era 32-bit Source binary (bin/linux32/srcds) cannot load game modules on modern systems; exits immediately |
| dysserver | Dystopia: 2006-era 32-bit Source binary (bin/linux32/srcds) cannot load game modules on modern systems; exits immediately |
| accserver | SteamCMD app 1430110 requires authentication (No subscription) |
| alienarenaserver | SteamCMD app 629540 reports success but installs no game files (no Linux depot) |
| argoserver | SteamCMD app 563930 installs no Linux-compatible executable |
| ark | SteamCMD app 376030 is 23GB; too large for automated CI testing |
| arma2coserver | SteamCMD app 33935 requires authentication (No subscription) |
| arma3altislifeserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3desolationreduxserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3epochserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3exileserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3headlessserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3server | SteamCMD app 233780 requires authentication (No subscription) |
| arma3wastelandserver | SteamCMD app 233780 requires authentication (No subscription) |
| atsserver | SteamCMD app 2239530 installs no Linux-compatible dedicated server binary (americantruck_server not present) |
| atlasserver | Docker-first validation 2026-05-29: the checked-in lane now seeds install-local Steam bootstrap state for the `steamcmd-linux` runtime, and a focused rerun under `/media/cosmosquark/a55b079e-515f-4798-a120-b1e69dda0b22/useme` proved the remaining blocker is no longer missing compatibility libraries. SteamCMD was actively populating `steamapps/downloading/1006030` (about `25G`) and the staged `ShooterGame/Binaries/Linux/ShooterGameServer` reproduced an immediate `Signal 11 caught.` crash inside the validated Docker image; `ldd` resolved the legacy OpenSSL/protobuf/Steam dependencies cleanly, so the exact remaining blocker is an early ATLAS binary segfault before A2S `info` / `query` can come up. |
| battlebitserver | SteamCMD app 689410 installs no Linux-compatible dedicated server binary (executable file not found) |
| bf1942server | Download domain bf1942.lightcubed.com is dead |
| bfvserver | Download URL (GameFront) is dead or gated |
| boserver | SteamCMD app 416881 requires authentication (No subscription) |
| brokeprotocolserver | SteamCMD app 696370 returns Invalid platform on Linux; Windows-only |
| citadelserver | SteamCMD app 489650 installs no Linux-compatible dedicated server binary (executable file not found) |
| chivalryserver | SteamCMD app 220070 now repairs the missing `PhysXUpdateLoader.so` alias, syncs the managed engine ports, and exposes the install-root Steam library paths so the Linux binary can locate `steamclient.so`, but anonymous startup still aborts in `SteamAPI_Init()` / `SteamAPI_IsSteamRunning()` before A2S `query` / `info` ever become reachable |
| conanexiles | SteamCMD app 443030 installs no Linux-compatible dedicated server binary (ConanSandboxServer not present) |
| counterstrikeglobaloffensive | SteamCMD app 740 installs legacy CS:GO build 1575; server reaches Steam, receives MasterRequestRestart, and self-shuts down while hibernating. Official CS2 dedicated servers were merged into app 730. |
| cryofallserver | SteamCMD app 1061710 installs no Linux-compatible dedicated server binary (CryoFall_Server not present) |
| dabserver | Dedicated server binary segfaults on startup |
| deadpolyserver | SteamCMD app 2208380 installs no Linux-compatible dedicated server binary (executable file not found) |
| deadmatterserver | SteamCMD app 1110990 requires authentication (No subscription) |
| dayzarma2epochserver | SteamCMD app 33935 requires authentication (No subscription) |
| dayzserver | SteamCMD app 223350 requires authentication (No subscription) |
| ets2server | SteamCMD app 1948160 installs the Linux dedicated server, but anonymous startup exits because the required exported server packages/settings file is missing; generate it from an owned ETS2 client with `export_server_packages` before the server can finish startup |
| foundryserver | SteamCMD app 2915550 installs no Linux-compatible dedicated server binary (FoundryDedicatedServer not present) |
| hurtworldserver | SteamCMD app 405100 installs no Linux-compatible dedicated server binary (HurtworldDedicated not present) |
| hzserver | SteamCMD app 2728330 installs no Linux-compatible dedicated server binary (executable file not found) |
| iosserver | IOSoccer dedicated server segfaults on startup |
| jc2server | SteamCMD app 261140 installs no Linux-compatible dedicated server binary (openjc2-server not present) |
| jc3server | SteamCMD app 619960 installs no Linux-compatible dedicated server binary (executable file not found) |
| jk2server | JK2 download URL returns 404 |
| kfserver | SteamCMD app 215360 requires authentication (No subscription) |
| l4d2server | SteamCMD app 222860 returns Invalid platform on Linux |
| lastoasisserver | SteamCMD download timeout; likely too large for automated CI testing |
| longvinterserver | Longvinter dedicated server (Steam app 1639880) crashes during startup with missing BlueprintableOnlineBeacons/DiscordRpc packaged scripts; game and query ports never open |
| mw3server | SteamCMD app 115310 requires authentication (No subscription) |
| ndserver | SteamCMD app 111710 installs incomplete Nuclear Dawn content (missing core game files); server crashes after loading Game_srv.so |
| nightingale | SteamCMD download timeout; likely too large for automated CI testing |
| ohdserver | SteamCMD app 950900 installs no Linux-compatible dedicated server binary (executable file not found) |
| police1013server | SteamCMD app 2691380 requires authentication (No subscription) |
| pvrserver | Docker-primary Pavlov VR setup/start/stop now work on the `steamcmd-linux` runtime image, and the status-helper port (`port + 400`) is launched and UDP-bound, but promotion is still blocked because raw A2S probes to that helper port time out from both the host and inside the container. AlphaGSM `query` / `info` still fall back to generic TCP reachability, so the required A2S lifecycle proof is not complete yet. |
| pcars2server | SteamCMD app 413770 requires authentication (No subscription) |
| q4server | Quake 4 download URL returns 404 |
| roserver | SteamCMD app 223250 requires authentication (No subscription) |
| rwserver | SteamCMD app 339010 installs no Linux-compatible dedicated server binary (server.jar not present) |
| sampserver | Download domain files.sa-mp.com is dead |
| seserver | SteamCMD app 298740 installs no Linux-compatible dedicated server binary (executable file not found) |
| sevendaystodie | SteamCMD |
| sfcserver | SourceForts Classic requires Half-Life 2: Deathmatch plus Source SDK Base 2013 Multiplayer (Steam app 243750); anonymous SteamCMD app 244310 lacks required runtime modules and exits at soundemittersystem.so |
| skyrimtogetherrebornserver | TiltedEvolution has no GitHub release assets |
| starbound | SteamCMD app 211820 installs no Linux-compatible dedicated server binary (linux64/starbound_server not present) |
| stationeersserver | Stationeers dedicated server stalls under Unity NullGfxDevice in headless CI after SetConsoleOutputCP startup exception; game port never opens |
| tiserver | SteamCMD app 412680 installs no Linux-compatible dedicated server binary (executable file not found) |
| veinserver | SteamCMD app 2131400 download timeout; likely too large for automated CI testing |
| vrserver | SteamCMD app 1829350 installs no Linux-compatible dedicated server binary (executable file not found) |
| wreckfestserver | SteamCMD app 361580 installs no Linux-compatible dedicated server binary (WreckfestServer not present) |
| zmrserver | SteamCMD app 244310 installs incomplete Zombie Master: Reborn content (only cfg scaffold, no mod payload) |
| zpsserver | Dedicated server binary segfaults on startup |

## SKIPPED (72)

Tests with `pytest.mark.skip` or "a `require_proton()` / `require_command()` guard — need a prerequisite before they can run.

| Test | Skip reason |
|------|-------------|
| stormworksserver | Wine: SteamCMD app 1247090 is now a redirect stub; server64.exe starts under Wine but produces no console output (redirect message appears in a Windows message box, not stdout); test waits full 300s before skipping |
| arksurvivalascended | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 2430930 |
| astroneerserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 728470 |
| blackwakeserver | Wine: bundled upstream `SERVER GUIDE.txt` documents Windows-only dedicated servers; managed `Server.cfg` / `gamemode=7` / `queryport` flow still stops before query-ready state with Steam game-server init failures and repeated `BotHandler` crashes, and manual Proton experiments with explicit `STEAM_COMPAT_CLIENT_INSTALL_PATH` / `-configFile` did not produce a lifecycle pass — app 423410 |
| darkandlightserver | Wine/Proton validation 2026-05-29: the current branch no longer reaches even the narrowed generic-UDP contract. `alphagsm start` can still return success, but the managed `screen` session dies before `DNL/Saved/Logs/DNL.log` is created or either the game port or `queryport 27016` binds, and direct Proton repros still leave orphaned `DNLServer.exe` children with no log or listener. |
| ducksideserver | SteamCMD app 2690320 requires authentication (No subscription) |
| empyrionserver | Wine/Proton lane 2026-05-29: AlphaGSM now keeps the direct dedicated contract on `DedicatedServer/EmpyrionDedicated.exe` and reads the real Linux runtime log at `Logs/alphagsm-dedicated.log`. A bounded AlphaGSM-managed host repro kept the direct dedicated process alive for 240 seconds, synced `ServerConfig.Srv_Port` to `46319`, created `Saves/Games/DediGame`, and advanced the stable dedicated log to `Started a new game`, but repeated probes still showed no listener on either the synced main port or the documented telnet port `30004`, and `query` / `info --json` continued to fail with `TCP ping failed: [Errno 111] Connection refused`. `EmpyrionLauncher.exe -startDedi` still falls back to the old `Failed to create batch mode window: Success.` dead end. |
| fearthenightserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 764940 |
| heatserver | Wine/Proton validation 2026-05-29: AlphaGSM now targets the real `Server.exe`, resolves query/info on the managed `queryport`, and uses the same `xvfb-run` + Proton headless wrapper contract as the bounded live smoke. Do not mark enabled yet: focused runtime evidence shows Heat can log `Game has started.` under `Logs/Console*.txt` / `Logs/Dedi*.txt`, but the checked-in readiness path still watches the stale root `server.log` contract and needs that log/query wiring corrected before promotion. |
| hellletlooseserver | SteamCMD app 822500 requires authentication (No subscription) |
| icarusserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 2089300 |
| lifeisfeudalserver | Wine: server starts but exits immediately — requires MySQL/MariaDB running on localhost (CmDb connection error #2002); MySQL skip guard added to test; app 320850 |
| medievalengineersserver | Proton starts but Medieval Engineers exits before producing server logs or readiness markers; no running process remains for stop/query |
| miscreatedserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 302200 |
| motortownserver | SteamCMD app 2223650 requires authentication (No subscription) |
| noonesurvivedserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 2329680 |
| notdserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 1420710 |
| outpostzeroserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 762880 |
| q3server | Direct download now installs the public ioquake3 Linux engine build, but CI lacks the licensed Quake III `baseq3/pak0.pk3` data required to start the dedicated server |
| reignofkingsserver | SteamCMD app 381690 requires authentication (No subscription) |
| returntomoriaserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 3349480 |
| ror2server | SteamCMD app 1180760 requires authentication (No subscription) |
| saleblazersserver | Wine validation 2026-05-29: the current non-headless `xvfb-run` + SDL `x11` + dummy audio + software-GL lane is clearly further than the old NullGfx path, and fresh repros confirm the upstream `-config <DedicatedServerConfig.json>` flow is real on Linux/Wine. The exact blocker is now narrower: the main game reaches `Launching server...`, `Config file found! Loading config from PATH ./DedicatedServerConfig.json`, and `Starting server console window process...`, while the generated Proton `ServerConsoleLogs/ServerConsole_*.log` only reaches `Waiting for Main Game Connection...`; the run still advertises `Port 55000` in the early multicast line instead of the configured hosting port and never progresses to `Server hosted on port ...` or a queryable A2S state. |
| scumserver | Wine: SteamCMD download timed out (>60 min) even with extended timeout; app 3792580 (SCUM) is extremely large — run with extended timeout and no competing downloads |
| sniperelite4server | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 568880 |
| sonsoftheforestserver | Launcher now targets `SonsOfTheForestDS.exe` directly instead of the legacy batch wrapper, and CI now uses a 60 minute setup timeout for the large SteamCMD payload (app 2465200) |
| bannerlordserver | Docker-path validation 2026-05-29: treat the module's existing `steamcmd-linux` runtime as the supported lane on `release_v1`, not a host-`dotnet` prerequisite. The stale published `ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest` image on the current host still fails earlier with `exec: "dotnet": executable file not found in $PATH`, but the branch-local `alphagsm-steamcmd-linux-runtime:bannerlord-dotnet` image proves the remaining blocker is deeper: SteamCMD setup for app `1863440` succeeds, `.NET 6.0.36` is present, and `dotnet TaleWorlds.Starter.DotNetCore.Linux.dll ...` still segfaults immediately while the managed container exits `139` before A2S `query` or `info` can come up. |
| starruptureserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 3809400 |
| staxelserver | SteamCMD app 755170 requires authentication (No subscription) |
| subsistenceserver | Wine/Proton validation 2026-05-28: app `1362640` still fails before AlphaGSM can reach A2S readiness; forced-Proton headless launch crashes in UE3 global-shader compilation, and the Wine-plus-`xvfb-run` variant changes the failure mode but still exits on later shader/compiler/runtime errors |
| ahlserver | HLDS mod maps not available via SteamCMD |
| aloftserver | SteamCMD app requires authentication |
| arma3_altislife | Arma 3 variant (needs base arma3server) |
| arma3_desolationredux | Arma 3 variant (needs base arma3server) |
| arma3_epoch | Arma 3 variant (needs base arma3server) |
| arma3_exile | Arma 3 variant (needs base arma3server) |
| arma3_headless | Arma 3 variant (needs base arma3server) |
| arma3_vanilla | Arma 3 variant (needs base arma3server) |
| arma3_wasteland | Arma 3 variant (needs base arma3server) |
| bbserver | HLDS mod maps not available via SteamCMD |
| brickadiaserver | SteamCMD app requires authentication |
| cod2server | Archive/download prerequisite |
| cod4server | Archive/download prerequisite |
| coduoserver | Archive/download prerequisite |
| codwawserver | Archive/download prerequisite |
| dstserver | DST requires a Klei cluster_token and cluster config to start; server exits immediately without them |
| ecoserver | EcoServer crashes on startup; possible missing runtime dependency (libssl or glibc version mismatch) |
| etlegacyserver | Archive/download prerequisite |
| gravserver | SteamCMD/platform issue |
| gtafivemserver | Requires txAdmin/authentication |
| hogwarpserver | SteamCMD/platform issue |
| identityserver | SteamCMD app requires authentication |
| interstellarriftserver | SteamCMD app requires authentication |
| kerbalspaceprogramserver | SteamCMD/platform issue |
| minecraft_bedrock | Minecraft.net Bedrock download page is JavaScript-rendered; URL scraper returns no results (module disabled) |
| minecraft_bungeecord | Java proxy (needs download URL) |
| minecraft_custom | Custom jar (needs user-supplied URL) |
| minecraft_tekkit | TechnicPack download page returns 403 Forbidden; server download URL unavailable |
| mtaserver | Download/platform prerequisite |
| mxbikesserver | Download prerequisite |
| nsserver | HLDS mod maps not available via SteamCMD |
| pathoftitansserver | SteamCMD app requires authentication |
| qlserver | Quake Live dedicated server (qzeroded.x64) exits immediately on startup; requires Steam authentication or specific server configuration |
| redmserver | Requires txAdmin/authentication |
| rtcwserver | Download prerequisite |
| soulmask | Soulmask server exits unexpectedly on startup; requires investigation of runtime configuration or library requirements |
| subnauticaserver | SteamCMD/platform issue |
| tsserver | HLDS mod maps not available via SteamCMD |
| twserver | SteamCMD app requires authentication |
| ut2k4server | Download prerequisite |
| vintagestoryserver | Download prerequisite |
| vsserver | HLDS mod maps not available via SteamCMD |

All integration tests have been tested and categorized. No untested servers remain.
