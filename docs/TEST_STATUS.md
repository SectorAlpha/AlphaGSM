# Integration Test Status

Last updated: 2026-05-19

## Summary

Tracker note: on 2026-05-15 the live `disabled_servers.conf` gate was reconciled
with already-supported Wine/Proton modules that were still blocked from `create`.
The status rows below already reflected those modules as active support surfaces;
this pass aligned the runtime gate with that existing tracker state.

| Status   | Count |
|----------|-------|
| PASSED   | 103      |
| DISABLED | 73      |
| SKIPPED  | 61      |

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.

## Counter-Strike Split

- `counterstrike2` and `cs2server` are the current CS2 surface. They now have a dedicated integration test and smoke runner, and they are not listed in `disabled_servers.conf`.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by Steam app `740` and are disabled.

## PASSED (103)

| Test | Type |
|------|------|
| acserver | SteamCMD |
| ahl2server | SteamCMD (Source) |
| armarserver | SteamCMD |
| atlasserver | SteamCMD — PASSED 2026-05-19; readiness now polls `info --json` until protocol `a2s` on the query path instead of depending on absent log markers |
| avserver | SteamCMD |
| archive_backed_installs | Archive |
| bb2server | SteamCMD (Source) |
| btlserver | SteamCMD |
| btserver | SteamCMD |
| bdserver | SteamCMD (GoldSrc) |
| bmdmserver | SteamCMD (Source) |
| ccserver | SteamCMD (Source) |
| chivalryserver | SteamCMD — PASSED 2026-05-19; the launch URL now passes the configured `Port=` value to `UDKGameServer-Linux`, the dedicated `queryport` is wired through setup/runtime, and smoke/integration validate through the real `a2s` endpoint |
| colserver | SteamCMD |
| cod2server | Direct download — BLOCKED 2026-05-19; the default archive lacks localized base assets (`main/localized_*.iwd` or `main/default_localize_mp.cfg`), and setup now fails fast instead of timing out after `start` |
| counterstrike2 | SteamCMD (Source 2) — PASSED 2026-04-08 |
| csczserver | SteamCMD (GoldSrc) |
| csserver | SteamCMD (GoldSrc) |
| cssserver | SteamCMD (Source) |
| craftopiaserver | SteamCMD |
| dayofdragonsserver | SteamCMD |
| darkandlightserver | SteamCMD (Proton) — PASSED 2026-05-19; the module now uses the fixed Wine-first Linux wrapper path again, and smoke/integration validate through the real `a2s` info/query surface instead of depending on the historical `DNL.log` path |
| dmcserver | SteamCMD (GoldSrc) |
| dodserver | SteamCMD (GoldSrc) |
| dodsserver | SteamCMD (Source) |
| doiserver | SteamCMD (Source) |
| emserver | SteamCMD (Source) — PASSED 2026-05-19; the Source lifecycle test now drives startup, hibernation handling, `info --json` protocol `a2s`, query/info, and clean shutdown |
| empyrionserver | SteamCMD (Proton) — PASSED 2026-05-19; the server launches `DedicatedServer/EmpyrionDedicated.exe`, uses the corrected Wine/Proton startup contract, and smoke/integration now require `info --json` protocol `a2s` after readiness |
| ets2server | SteamCMD — PASSED 2026-05-19; readiness now polls `info --json` until protocol `a2s` instead of depending on absent log markers |
| exfilserver | SteamCMD |
| fofserver | SteamCMD (Source) |
| frozenflameserver | SteamCMD |
| gmodserver | SteamCMD (Source) |
| goldeneyesourceserver | Direct download |
| heatserver | SteamCMD (Proton) — PASSED 2026-05-19; the server launches `Server.exe`, writes readiness to `server.log`, and smoke/integration now wait for `info --json` protocol `a2s` before query/info |
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
| mumbleserver | Docker runtime — PASSED 2026-05-18; standard integration/smoke now drive the module through the shared `simple-tcp` Docker runtime image because upstream does not publish an anonymous Linux server binary, while process mode still works when a host `mumble-server`/`murmurd` package is installed |
| mordserver | SteamCMD |
| necserver | SteamCMD |
| nmrihserver | SteamCMD (Source) |
| opforserver | SteamCMD (GoldSrc) |
| palworld | SteamCMD |
| pcarserver | SteamCMD — PASSED 2026-05-19; readiness now polls `info --json` until protocol `a2s` instead of depending on absent log markers |
| primalcarnageextinctionserver | SteamCMD (Proton) — PASSED 2026-05-19; the UE3 server launches with `-log`, writes readiness to `PrimalCarnageGame/Logs/Launch.log`, and smoke/integration now require `info --json` protocol `a2s` before query/info |
| projectzomboid | SteamCMD |
| pvrserver | SteamCMD — PASSED 2026-05-19; readiness now polls `info --json` until protocol `a2s` on the query port instead of depending on absent log markers |
| q2server | Direct download — PASSED 2026-05-18; setup now builds Yamagi Quake II from source, stages the official demo `baseq2` data for anonymous installs, defaults fresh servers to `demo1`, and query/info use the dedicated Quake II `status` protocol |
| qwserver | Direct download — PASSED 2026-05-18; setup now stages the public nQuake shareware, KTX runtime, configs, and core maps needed for anonymous MVDSV installs, launches with `-game ktx`, and query/info use the dedicated QuakeWorld `status` protocol |
| pvkiiserver | SteamCMD (Source) |
| ricochetserver | SteamCMD (GoldSrc) |
| rimworldtogetherserver | Direct download |
| rs2server | SteamCMD (Proton) — PASSED 2026-05-19; `VNGame.exe` now uses the corrected Wine-first Linux wrapper path, readiness comes from `ROGame/Logs/Launch.log`, and smoke/integration wait for `info --json` protocol `a2s` with the longer CI startup budget |
| rust | SteamCMD |
| saleblazersserver | SteamCMD (Proton) — PASSED 2026-05-19; the server writes readiness to `server.log` via `-logFile`, and smoke/integration now require `info --json` protocol `a2s` before query/info |
| satisfactory | SteamCMD |
| silicaserver | SteamCMD |
| scpslserver | SteamCMD |
| smallandserver | SteamCMD |
| solserver | SteamCMD |
| sonsoftheforestserver | SteamCMD (Proton) — PASSED 2026-05-19; the launcher now targets `SonsOfTheForestDS.exe` directly instead of the legacy batch wrapper, and CI uses the extended setup budget needed for the large SteamCMD payload |
| squad44server | SteamCMD |
| squadserver | SteamCMD |
| ss14server | Robust/HTTP status — PASSED 2026-05-19; manifest-based downloads install correctly, AlphaGSM syncs `server_config.toml`, smoke/integration validate through `info --json` protocol `robust_status`, and CI now installs `.NET 10` while host/runtime usage still requires `dotnet` |
| stnserver | SteamCMD |
| subsistenceserver | SteamCMD (Proton) — PASSED 2026-05-19; the UE3 D3D crash is mitigated with `LIBGL_ALWAYS_SOFTWARE=1`, readiness comes from `*/Logs/Launch.log`, and smoke/integration now require `info --json` protocol `a2s` before query/info |
| svenserver | SteamCMD (GoldSrc) |
| terraria_vanilla | Direct download |
| terratechworldsserver | SteamCMD (Proton) — PASSED 2026-05-19; readiness comes from `Saved/Logs/TT2.log`, and smoke/integration now require `info --json` protocol `a2s` before query/info |
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
| insserver | Smoke re-enabled: PASSED 2026-03-28; smoke now waits for Source startup markers and `info --json` protocol `a2s` |
| inssserver | Smoke re-enabled: PASSED 2026-03-28; smoke now waits for startup markers and `info --json` protocol `a2s` on the Sandstorm query path |
| ts3server | Smoke re-enabled: Direct download — PASSED 2026-03-28; smoke now waits for `ServerQuery created` and `info --json` protocol `ts3` |

## DISABLED (73)

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
| battlebitserver | SteamCMD app 689410 installs no Linux-compatible dedicated server binary (executable file not found) |
| bf1942server | Download domain bf1942.lightcubed.com is dead |
| bfvserver | Download URL (GameFront) is dead or gated |
| boserver | SteamCMD app 416881 requires authentication (No subscription) |
| bobserver | SteamCMD app 882430 download timeout; likely too large for automated CI testing |
| brokeprotocolserver | SteamCMD app 696370 returns Invalid platform on Linux; Windows-only |
| citadelserver | SteamCMD app 489650 installs no Linux-compatible dedicated server binary (executable file not found) |
| conanexiles | SteamCMD app 443030 installs no Linux-compatible dedicated server binary (ConanSandboxServer not present) |
| counterstrikeglobaloffensive | SteamCMD app 740 installs legacy CS:GO build 1575; server reaches Steam, receives MasterRequestRestart, and self-shuts down while hibernating. Official CS2 dedicated servers were merged into app 730. |
| cryofallserver | SteamCMD app 1061710 installs no Linux-compatible dedicated server binary (CryoFall_Server not present) |
| dabserver | Dedicated server binary segfaults on startup |
| deadpolyserver | SteamCMD app 2208380 installs no Linux-compatible dedicated server binary (executable file not found) |
| deadmatterserver | SteamCMD app 1110990 requires authentication (No subscription) |
| dayzarma2epochserver | SteamCMD app 33935 requires authentication (No subscription) |
| dayzserver | SteamCMD app 223350 requires authentication (No subscription) |
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

## SKIPPED (78)

Tests with `pytest.mark.skip` or "a `require_proton()` / `require_command()` guard — need a prerequisite before they can run.

| Test | Skip reason |
|------|-------------|
| stormworksserver | Wine: SteamCMD app 1247090 is now a redirect stub; server64.exe starts under Wine but produces no console output (redirect message appears in a Windows message box, not stdout); test waits full 300s before skipping |
| arksurvivalascended | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 2430930 |
| astroneerserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 728470 |
| blackwakeserver | Wine: exe BlackwakeServer.exe confirmed; -batchmode -nographics added; fails with 'already running' — investigating process detection false positive — app 423410 |
| ducksideserver | SteamCMD app 2690320 requires authentication (No subscription) |
| fearthenightserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 764940 |
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
| scumserver | Wine: SteamCMD download timed out (>60 min) even with extended timeout; app 3792580 (SCUM) is extremely large — run with extended timeout and no competing downloads |
| sniperelite4server | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 568880 |
| bannerlordserver | Re-enabled from disabled: anonymous SteamCMD installs app 1863440 successfully, the module now targets `bin/Linux64_Shipping_Server/TaleWorlds.Starter.DotNetCore.Linux.dll`, Docker launches from the correct subdirectory, and the shared `steamcmd-linux` image now carries both .NET 6 and .NET 10; Bannerlord is still blocked because the dedicated server exits with a native `SIGSEGV` before `info --json`/A2S becomes available, and setup validation can additionally flake on SteamCMD state `0x202` |
| starruptureserver | Wine: SteamCMD download timed out under the default integration setup budget; CI now uses a 60 minute setup timeout for app 3809400 |
| staxelserver | SteamCMD app 755170 requires authentication (No subscription) |
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
| cod4server | Direct download — BLOCKED 2026-05-19; the default archive lacks required base assets (`fileSysCheck.cfg` and localized `main/*.iwd` content), and setup now fails fast instead of hanging in smoke |
| codserver | Direct download — PASSED 2026-05-19; built-in `fs_game main` is suppressed, query/info are routed through the live TCP game port, and smoke now validates the real dedicated process end to end |
| coduoserver | Direct download — BLOCKED 2026-05-19; the package now extracts with the corrected executable and archive metadata, but the default upload still lacks base Call of Duty assets (`main/pak0.pk3` or `main/default_mp.cfg`), so setup fails fast |
| codwawserver | Direct download — BLOCKED 2026-05-19; the current upstream payload is not a valid bzip2 tarball, so setup fails during extraction even after normalizing the archive metadata |
| codwawserver | Direct download — BLOCKED 2026-05-19; setup now uses a pragmatic LinuxGSM tar.xz archive instead of the broken old payload, but the package still lacks required base World at War assets (`main/pak0.pk3` or `main/default_mp.cfg`), so setup fails fast |
| dstserver | DST requires a Klei cluster_token and cluster config to start; server exits immediately without them |
| ecoserver | EcoServer crashes on startup; possible missing runtime dependency (libssl or glibc version mismatch) |
| etlegacyserver | Archive/download prerequisite |
| gravserver | SteamCMD/platform issue |
| gtafivemserver | Requires txAdmin/authentication |
| hogwarpserver | SteamCMD/platform issue |
| identityserver | SteamCMD app requires authentication |
| interstellarriftserver | SteamCMD app requires authentication |
| kerbalspaceprogramserver | SteamCMD/platform issue |
| minecraft_bedrock | Direct download — PASSED 2026-05-19; setup still falls back to the last verified official Bedrock Linux archive when Minecraft.net hides the live Linux link, and query/info/smoke now use the real Bedrock RakNet UDP ping |
| minecraft_bungeecord | Direct download — PASSED 2026-05-19; setup now resolves the latest successful Spigot Jenkins BungeeCord jar by default, writes the configured listener port into `config.yml`, and passes smoke plus focused integration coverage over the normal TCP/SLP proxy surface |
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
