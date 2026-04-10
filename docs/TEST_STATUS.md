# Integration Test Status

Last updated: 2026-04-10

## Summary

| Status   | Count |
|----------|-------|
| PASSED   | 83      |
| DISABLED | 74      |
| SKIPPED  | 78      |

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.

## Counter-Strike Split

- `counterstrike2` and `cs2server` are the current CS2 surface. They now have a dedicated integration test and smoke runner, and they are not listed in `disabled_servers.conf`.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by Steam app `740` and are disabled.

## PASSED (83)

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
| minecraft_vanilla | Direct download |
| minecraft_velocity | Direct download |
| minecraft_waterfall | Direct download |
| memoriesofmarsserver | SteamCMD |
| mordserver | SteamCMD |
| necserver | SteamCMD |
| nmrihserver | SteamCMD (Source) |
| opforserver | SteamCMD (GoldSrc) |
| palworld | SteamCMD |
| projectzomboid | SteamCMD |
| pvkiiserver | SteamCMD (Source) |
| ricochetserver | SteamCMD (GoldSrc) |
| rimworldtogetherserver | Direct download |
| rust | SteamCMD |
| satisfactory | SteamCMD |
| silicaserver | SteamCMD |
| scpslserver | SteamCMD |
| smallandserver | SteamCMD |
| solserver | SteamCMD |
| squad44server | SteamCMD |
| squadserver | SteamCMD |
| stnserver | SteamCMD |
| svenserver | SteamCMD (GoldSrc) |
| terraria_vanilla | Direct download |
| tf2 | SteamCMD (Source) |
| tfcserver | SteamCMD (GoldSrc) |
| thefrontserver | SteamCMD |
| unturned | SteamCMD |
| ut99server | Direct download |
| valheim | SteamCMD |
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
| remnantsserver | SteamCMD (Wine) — exe changed to RemSurvivalServer.exe; added -log -unattended; awaiting retest |
| readyornotserver | SteamCMD (Wine) — PASSED 2026-03-28 |
| insserver | SteamCMD (Source) — PASSED 2026-03-28 |
| inssserver | SteamCMD — PASSED 2026-03-28 |
| ts3server | Direct download — PASSED 2026-03-28 |

## DISABLED (74)

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
| atlasserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| bannerlordserver | SteamCMD app 1863440 installs no Linux-compatible dedicated server binary (executable file not found) |
| battlebitserver | SteamCMD app 689410 installs no Linux-compatible dedicated server binary (executable file not found) |
| bf1942server | Download domain bf1942.lightcubed.com is dead |
| bfvserver | Download URL (GameFront) is dead or gated |
| boserver | SteamCMD app 416881 requires authentication (No subscription) |
| bobserver | SteamCMD app 882430 download timeout; likely too large for automated CI testing |
| brokeprotocolserver | SteamCMD app 696370 returns Invalid platform on Linux; Windows-only |
| citadelserver | SteamCMD app 489650 installs no Linux-compatible dedicated server binary (executable file not found) |
| chivalryserver | Server starts but crashes during initialization before log markers appear (crash pattern) |
| conanexiles | SteamCMD app 443030 installs no Linux-compatible dedicated server binary (ConanSandboxServer not present) |
| counterstrikeglobaloffensive | SteamCMD app 740 installs legacy CS:GO build 1575; server reaches Steam, receives MasterRequestRestart, and self-shuts down while hibernating. Official CS2 dedicated servers were merged into app 730. |
| cryofallserver | SteamCMD app 1061710 installs no Linux-compatible dedicated server binary (CryoFall_Server not present) |
| dabserver | Dedicated server binary segfaults on startup |
| deadpolyserver | SteamCMD app 2208380 installs no Linux-compatible dedicated server binary (executable file not found) |
| deadmatterserver | SteamCMD app 1110990 requires authentication (No subscription) |
| dayzarma2epochserver | SteamCMD app 33935 requires authentication (No subscription) |
| dayzserver | SteamCMD app 223350 requires authentication (No subscription) |
| emserver | SteamCMD app 460040 returns `Missing configuration` (state `0x202`); anonymous install is not usable in CI |
| ets2server | SteamCMD downloads successfully but server never outputs expected readiness markers |
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
| pcarserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| pvrserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| pcars2server | SteamCMD app 413770 requires authentication (No subscription) |
| q3server | ioquake3 has no GitHub releases; download 404 |
| q4server | Quake 4 download URL returns 404 |
| roserver | SteamCMD app 223250 requires authentication (No subscription) |
| rwserver | SteamCMD app 339010 installs no Linux-compatible dedicated server binary (server.jar not present) |
| sampserver | Download domain files.sa-mp.com is dead |
| seserver | SteamCMD app 298740 installs no Linux-compatible dedicated server binary (executable file not found) |
| sevendaystodie | SteamCMD app 294420 anonymous install repeatedly returns state 0x202; dedicated server payload is not installable in CI |
| sfcserver | SourceForts Classic requires Half-Life 2: Deathmatch plus Source SDK Base 2013 Multiplayer (Steam app 243750); anonymous SteamCMD app 244310 lacks required runtime modules and exits at soundemittersystem.so |
| skyrimtogetherrebornserver | TiltedEvolution has no GitHub release assets |
| ss14server | SS14 CDN returns 404 |
| starbound | SteamCMD app 211820 installs no Linux-compatible dedicated server binary (linux64/starbound_server not present) |
| stationeersserver | Stationeers dedicated server stalls under Unity NullGfxDevice in headless CI after SetConsoleOutputCP startup exception; game port never opens |
| tiserver | SteamCMD app 412680 installs no Linux-compatible dedicated server binary (executable file not found) |
| trackmaniaserver | TrackMania download URL returns 403 |
| warbandserver | TaleWorlds download page blocks automated access (HTTP 403) |
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
| arksurvivalascended | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2430930 (ARK Survival Ascended) is extremely large — run individually with extended timeout |
| astroneerserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 728470 — run individually to verify |
| blackwakeserver | Wine: exe BlackwakeServer.exe confirmed; -batchmode -nographics added; fails with 'already running' — investigating process detection false positive — app 423410 |
| darkandlightserver | Wine: server starts (runs at 39% CPU) but DNL/Saved/Logs/DNL.log not created within 300s under Wine; UE4 init is slow — START_TIMEOUT raised to 600s; needs retest |
| ducksideserver | SteamCMD app 2690320 requires authentication (No subscription) |
| empyrionserver | Wine: exe path fixed (DedicatedServer/EmpyrionDedicated.exe); needs individual retest — app 530870 |
| fearthenightserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 764940 — run individually to verify |
| heatserver | Wine: exe path fixed (was wrong exe name); needs individual retest — app 996600 |
| hellletlooseserver | SteamCMD app 822500 requires authentication (No subscription) |
| icarusserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2089300 (Icarus) is very large — run individually with extended timeout |
| lifeisfeudalserver | Wine: server starts but exits immediately — requires MySQL/MariaDB running on localhost (CmDb connection error #2002); MySQL skip guard added to test; app 320850 |
| medievalengineersserver | Proton starts but Medieval Engineers exits before producing server logs or readiness markers; no running process remains for stop/query |
| miscreatedserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 302200 — run individually to verify |
| motortownserver | SteamCMD app 2223650 requires authentication (No subscription) |
| noonesurvivedserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2329680 — run individually to verify |
| notdserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 1420710 — run individually to verify |
| outpostzeroserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 762880 — run individually to verify |
| primalcarnageextinctionserver | Wine: UE3 log path fixed (PrimalCarnageGame/Logs/Launch.log), -log flag added, START_TIMEOUT raised to 600s; awaiting retest — app 336400 |

| reignofkingsserver | SteamCMD app 381690 requires authentication (No subscription) |
| returntomoriaserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 3349480 — run individually to verify |
| ror2server | SteamCMD app 1180760 requires authentication (No subscription) |
| rs2server | Wine: server (VNGame.exe, app 418480) starts and stops cleanly under Wine but does not write expected log markers within 300s; likely writes logs to game-internal paths (Unreal Engine 3), not stdout; START_TIMEOUT raised to 600s — awaiting retest |
| saleblazersserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 3099600 — run individually to verify |
| scumserver | Wine: SteamCMD download timed out (>60 min) even with extended timeout; app 3792580 (SCUM) is extremely large — run with extended timeout and no competing downloads |
| sniperelite4server | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 568880 (Sniper Elite 4) is very large — run individually with extended timeout |
| sonsoftheforestserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2465200 (Sons of the Forest) is large — run individually with extended timeout |
| starruptureserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 3809400 — run individually to verify |
| staxelserver | SteamCMD app 755170 requires authentication (No subscription) |
| subsistenceserver | Wine: UE3 server D3D crash fixed with LIBGL_ALWAYS_SOFTWARE=1 (Mesa software renderer); -log flag added; test now checks */Logs/Launch.log via glob; START_TIMEOUT raised to 600s; awaiting retest — app 1141370 |
| terratechworldsserver | Wine: server runs but Saved/Logs/TT2.log not created within 300–460s; UE4 init is slow under Wine — START_TIMEOUT raised to 600s; needs retest |
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
| codserver | Archive/download prerequisite |
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
| mumbleserver | Direct download prerequisite |
| mxbikesserver | Download prerequisite |
| nsserver | HLDS mod maps not available via SteamCMD |
| pathoftitansserver | SteamCMD app requires authentication |
| q2server | Download prerequisite |
| qlserver | Quake Live dedicated server (qzeroded.x64) exits immediately on startup; requires Steam authentication or specific server configuration |
| qwserver | Download prerequisite |
| redmserver | Requires txAdmin/authentication |
| rtcwserver | Download prerequisite |
| soulmask | Soulmask server exits unexpectedly on startup; requires investigation of runtime configuration or library requirements |
| subnauticaserver | SteamCMD/platform issue |
| terraria_tshock | Download prerequisite |
| tsserver | HLDS mod maps not available via SteamCMD |
| twserver | SteamCMD app requires authentication |
| ut2k4server | Download prerequisite |
| vintagestoryserver | Download prerequisite |
| vsserver | HLDS mod maps not available via SteamCMD |

All integration tests have been tested and categorized. No untested servers remain.
