# Integration Test Status

Last updated: 2026-03-25

## Summary

| Status   | Count |
|----------|-------|
| PASSED   | 60    |
| DISABLED | 126   |
| SKIPPED  | 48    |
| RUNNABLE | 0     |

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.
- **RUNNABLE** — Test exists and has no skip marker but has not been confirmed passing yet.

## PASSED (56)

| Test | Type |
|------|------|
| acserver | SteamCMD |
| ahl2server | SteamCMD (Source) |
| archive_backed_installs | Archive |
| bb2server | SteamCMD (Source) |
| btlserver | SteamCMD |
| btserver | SteamCMD |
| bdserver | SteamCMD (GoldSrc) |
| bmdmserver | SteamCMD (Source) |
| ccserver | SteamCMD (Source) |
| csczserver | SteamCMD (GoldSrc) |
| csserver | SteamCMD (GoldSrc) |
| cssserver | SteamCMD (Source) |
| dayofdragonsserver | SteamCMD |
| dmcserver | SteamCMD (GoldSrc) |
| dodserver | SteamCMD (GoldSrc) |
| dodsserver | SteamCMD (Source) |
| doiserver | SteamCMD (Source) |
| emserver | SteamCMD (Source) |
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
| longvinterserver | SteamCMD |
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
| sevendaystodie | SteamCMD |
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
| valheim | SteamCMD |
| wfserver | SteamCMD |
| xntserver | Direct download |

## DISABLED (126)

| Test | Reason |
|------|--------|
| abfserver | SteamCMD app 2857200 returns Invalid platform on Linux |
| accserver | SteamCMD app 1430110 requires authentication (No subscription) |
| alienarenaserver | SteamCMD app 629540 reports success but installs no game files (no Linux depot) |
| argoserver | SteamCMD app 563930 installs no Linux-compatible executable |
| ark | SteamCMD app 376030 is 23GB; too large for automated CI testing |
| arksurvivalascended | SteamCMD app 2430930 is Windows-only (Win64/ArkAscendedServer.exe) |
| arma2coserver | SteamCMD app 33935 requires authentication (No subscription) |
| arma3altislifeserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3desolationreduxserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3epochserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3exileserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3headlessserver | SteamCMD app 233780 requires authentication (No subscription) |
| arma3server | SteamCMD app 233780 requires authentication (No subscription) |
| arma3wastelandserver | SteamCMD app 233780 requires authentication (No subscription) |
| armarserver | Arma Reforger server requires configs/server.json; module does not create it |
| askaserver | SteamCMD app 3246670 is Windows-only (AskaServer.exe) |
| astroneerserver | SteamCMD app 728470 is Windows-only (AstroServer.exe) |
| avserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| atsserver | SteamCMD app 2239530 installs no Linux-compatible dedicated server binary (americantruck_server not present) |
| atlasserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| battlecryoffreedomserver | SteamCMD app 1362540 is Windows-only (BCoF.exe) |
| bannerlordserver | SteamCMD app 1863440 installs no Linux-compatible dedicated server binary (executable file not found) |
| battlebitserver | SteamCMD app 689410 installs no Linux-compatible dedicated server binary (executable file not found) |
| bf1942server | Download domain bf1942.lightcubed.com is dead |
| bfvserver | Download URL (GameFront) is dead or gated |
| blackops3server | SteamCMD app 545990 is Windows-only (BlackOps3Server.exe) |
| blackwakeserver | SteamCMD app 423410 is Windows-only (Blackwake Dedicated Server.exe) |
| boserver | SteamCMD app 416881 requires authentication (No subscription) |
| bobserver | SteamCMD app 882430 download timeout; likely too large for automated CI testing |
| bsserver | Blade Symphony server layout changed; srcds_run.sh moved to bin/ subdirectory |
| brokeprotocolserver | SteamCMD app 696370 returns Invalid platform on Linux; Windows-only |
| colserver | SteamCMD app 748090 installs no Linux-compatible dedicated server binary (ColonyServer.x86_64 not present) |
| citadelserver | SteamCMD app 489650 installs no Linux-compatible dedicated server binary (executable file not found) |
| ckserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| chivalryserver | Server starts but crashes during initialization before log markers appear (crash pattern) |
| conanexiles | SteamCMD app 443030 installs no Linux-compatible dedicated server binary (ConanSandboxServer not present) |
| counterstrikeglobaloffensive | CS2/CS:GO (app 740) server binary fails to load; bundled libgcc_s.so.1 lacks GCC_7.0.0 required by system libstdc++.so.6 (Ubuntu 24.04) |
| cryofallserver | SteamCMD app 1061710 installs no Linux-compatible dedicated server binary (CryoFall_Server not present) |
| craftopiaserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| dabserver | Dedicated server binary segfaults on startup |
| deadpolyserver | SteamCMD app 2208380 installs no Linux-compatible dedicated server binary (executable file not found) |
| deadmatterserver | SteamCMD app 1110990 requires authentication (No subscription) |
| darkandlightserver | SteamCMD app 630230 is Windows-only (Win64/DNLServer.exe) |
| dayzarma2epochserver | SteamCMD app 33935 requires authentication (No subscription) |
| dayzserver | SteamCMD app 223350 requires authentication (No subscription) |
| ducksideserver | SteamCMD app 2690320 is Windows-only (DucksideServer.exe) |
| dysserver | Dystopia server layout changed; srcds_run.sh moved to bin/ subdirectory |
| empyrionserver | SteamCMD app 530870 is Windows-only (EmpyrionDedicated.exe) |
| enshrouded | SteamCMD app 2278520 installs no Linux-compatible dedicated server binary (enshrouded_server not present) |
| ets2server | SteamCMD downloads successfully but server never outputs expected readiness markers |
| fearthenightserver | SteamCMD app 764940 is Windows-only (Win64/MoonlightServer.exe) |
| foundryserver | SteamCMD app 2915550 installs no Linux-compatible dedicated server binary (FoundryDedicatedServer not present) |
| groundbranchserver | SteamCMD app 476400 is Windows-only (Win64-Shipping.exe) |
| heatserver | SteamCMD app 996600 is Windows-only (HeatServer.exe) |
| hellletlooseserver | SteamCMD app 822500 is Windows-only (HLLServer.exe) |
| hurtworldserver | SteamCMD app 405100 installs no Linux-compatible dedicated server binary (HurtworldDedicated not present) |
| hzserver | SteamCMD app 2728330 installs no Linux-compatible dedicated server binary (executable file not found) |
| icarusserver | SteamCMD app 2089300 is Windows-only (IcarusServer.exe) |
| insserver | Insurgency srcds_run has CRLF line endings; cannot exec |
| inssserver | Insurgency: Sandstorm (app 581330) module uses incorrect executable path; binary is at Insurgency/Binaries/Linux/ not install root |
| iosserver | IOSoccer dedicated server segfaults on startup |
| jc2server | SteamCMD app 261140 installs no Linux-compatible dedicated server binary (openjc2-server not present) |
| jc3server | SteamCMD app 619960 installs no Linux-compatible dedicated server binary (executable file not found) |
| jk2server | JK2 download URL returns 404 |
| kfserver | SteamCMD app 215360 requires authentication (No subscription) |
| l4d2server | SteamCMD app 222860 returns Invalid platform on Linux |
| lastoasisserver | SteamCMD download timeout; likely too large for automated CI testing |
| lifeisfeudalserver | SteamCMD app 320850 is Windows-only (ddctd_cm_yo_server.exe) |
| medievalengineersserver | SteamCMD app 367970 is Windows-only (MedievalEngineersDedicated.exe) |
| miscreatedserver | SteamCMD app 302200 is Windows-only (MiscreatedServer.exe) |
| motortownserver | SteamCMD app 2223650 is Windows-only (Win64/MotorTownServer.exe) |
| mw3server | SteamCMD app 115310 is Windows-only (iw5mp_server.exe) |
| mythofempiresserver | SteamCMD app 1794810 is Windows-only (Win64/MOEServer.exe) |
| ndserver | Nuclear Dawn dedicated server install is incomplete; gameinfo.txt missing |
| noonesurvivedserver | SteamCMD app 2329680 is Windows-only (WRSHServer.exe) |
| nightingale | SteamCMD download timeout; likely too large for automated CI testing |
| notdserver | SteamCMD app 1420710 is Windows-only (Win64/LFServer.exe) |
| outpostzeroserver | SteamCMD app 762880 is Windows-only (OutpostZeroServer.exe) |
| ohdserver | SteamCMD app 950900 installs no Linux-compatible dedicated server binary (executable file not found) |
| pixarkserver | SteamCMD app 824360 is Windows-only (PixARKServer.exe) |
| police1013server | SteamCMD app 2691380 requires authentication (No subscription) |
| pcarserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| pvrserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| pcars2server | SteamCMD app 413770 requires authentication (No subscription) |
| primalcarnageextinctionserver | SteamCMD app 336400 is Windows-only (PCEdedicated.exe) |
| q3server | ioquake3 has no GitHub releases; download 404 |
| q4server | Quake 4 download URL returns 404 |
| readyornotserver | SteamCMD app 950290 is Windows-only (ReadyOrNotServer.exe) |
| reignofdwarfserver | SteamCMD app 1999160 is Windows-only (ReignOfDwarfServer.exe) |
| reignofkingsserver | SteamCMD app 381690 is Windows-only (Server.exe) |
| remnantsserver | SteamCMD app 1141420 is Windows-only (StartServer.bat) |
| returntomoriaserver | SteamCMD app 3349480 is Windows-only (MoriaServer.exe) |
| ror2server | SteamCMD app 1180760 is Windows-only (Risk of Rain 2.exe) |
| roserver | SteamCMD app 223250 requires authentication (No subscription) |
| rs2server | SteamCMD app 418480 is Windows-only (Win64/VNGame.exe) |
| rwserver | SteamCMD app 339010 installs no Linux-compatible dedicated server binary (server.jar not present) |
| saleblazersserver | SteamCMD app 3099600 is Windows-only (Saleblazers.exe) |
| sampserver | Download domain files.sa-mp.com is dead |
| scpslserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| scumserver | SteamCMD app 3792580 is Windows-only (Win64/SCUMServer.exe) |
| seserver | SteamCMD app 298740 installs no Linux-compatible dedicated server binary (executable file not found) |
| sfcserver | SourceForts Classic install incomplete; sfclassic/gameinfo.txt missing |
| skyrimtogetherrebornserver | TiltedEvolution has no GitHub release assets |
| smallandserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| sniperelite4server | SteamCMD app 568880 is Windows-only (SniperElite4_DedicatedServer.exe) |
| sonsoftheforestserver | SteamCMD app 2465200 is Windows-only (SonsOfTheForestDS.exe) |
| ss14server | SS14 CDN returns 404 |
| starbound | SteamCMD app 211820 installs no Linux-compatible dedicated server binary (linux64/starbound_server not present) |
| starruptureserver | SteamCMD app 3809400 is Windows-only (StarRuptureServerEOS.exe) |
| stationeersserver | Can't start server that is already running (process management issue during setup) |
| staxelserver | SteamCMD app 755170 is Windows-only (Staxel.ServerWizard.exe) |
| stormworksserver | SteamCMD app 1247090 is Windows-only (server64.exe) |
| subsistenceserver | SteamCMD app 1362640 is Windows-only (Win32/run_dedicated_server.bat) |
| sunkenlandserver | SteamCMD app 2667530 is Windows-only (Sunkenland-DedicatedServer.exe) |
| terratechworldsserver | SteamCMD app 2533070 is Windows-only (TT2Server.exe) |
| theforestserver | SteamCMD app 556450 is Windows-only (TheForestDedicatedServer.exe) |
| tiserver | SteamCMD app 412680 installs no Linux-compatible dedicated server binary (executable file not found) |
| trackmaniaserver | TrackMania download URL returns 403 |
| ts3server | TeamSpeak downloads page layout changed; version scraper broken |
| warbandserver | TaleWorlds download page blocks automated access (HTTP 403) |
| veinserver | SteamCMD app 2131400 download timeout; likely too large for automated CI testing |
| vrserver | SteamCMD app 1829350 installs no Linux-compatible dedicated server binary (executable file not found) |
| wreckfestserver | SteamCMD app 361580 installs no Linux-compatible dedicated server binary (WreckfestServer not present) |
| wurmserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| zmrserver | Zombie Master Reborn install incomplete; zmr/gameinfo.txt missing |
| zpsserver | Dedicated server binary segfaults on startup |

## SKIPPED (48)

Tests with `pytest.mark.skip` in the test file — need prerequisite fixes before running.

| Test | Skip reason |
|------|-------------|
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
| ut99server | Download prerequisite |
| vintagestoryserver | Download prerequisite |
| vsserver | HLDS mod maps not available via SteamCMD |

## RUNNABLE (0)

All integration tests have been tested and categorized. No untested servers remain.