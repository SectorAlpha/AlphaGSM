# Integration Test Status

Last updated: 2026-03-27

## Summary

| Status   | Count |
|----------|-------|
| PASSED   | 66    |
| DISABLED | 82    |
| SKIPPED  | 86    |
| RUNNABLE | 0     |

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.
- **RUNNABLE** — Test exists and has no skip marker but has not been confirmed passing yet.

## PASSED (66)

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
| battlecryoffreedomserver | SteamCMD (Proton) |
| enshrouded | SteamCMD (Proton) |
| mythofempiresserver | SteamCMD (Proton) |
| reignofdwarfserver | SteamCMD (Proton) |
| sunkenlandserver | SteamCMD (Proton) |
| theforestserver | SteamCMD (Proton) |

## DISABLED (82)

| Test | Reason |
|------|--------|
| abfserver | SteamCMD app 2857200 returns Invalid platform on Linux |
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
| armarserver | Arma Reforger server requires configs/server.json; module does not create it |
| avserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| atsserver | SteamCMD app 2239530 installs no Linux-compatible dedicated server binary (americantruck_server not present) |
| atlasserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| bannerlordserver | SteamCMD app 1863440 installs no Linux-compatible dedicated server binary (executable file not found) |
| battlebitserver | SteamCMD app 689410 installs no Linux-compatible dedicated server binary (executable file not found) |
| bf1942server | Download domain bf1942.lightcubed.com is dead |
| bfvserver | Download URL (GameFront) is dead or gated |
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
| dayzarma2epochserver | SteamCMD app 33935 requires authentication (No subscription) |
| dayzserver | SteamCMD app 223350 requires authentication (No subscription) |
| dysserver | Dystopia server layout changed; srcds_run.sh moved to bin/ subdirectory |
| ets2server | SteamCMD downloads successfully but server never outputs expected readiness markers |
| foundryserver | SteamCMD app 2915550 installs no Linux-compatible dedicated server binary (FoundryDedicatedServer not present) |
| hurtworldserver | SteamCMD app 405100 installs no Linux-compatible dedicated server binary (HurtworldDedicated not present) |
| hzserver | SteamCMD app 2728330 installs no Linux-compatible dedicated server binary (executable file not found) |
| insserver | Insurgency srcds_run has CRLF line endings; cannot exec |
| inssserver | Insurgency: Sandstorm (app 581330) module uses incorrect executable path; binary is at Insurgency/Binaries/Linux/ not install root |
| iosserver | IOSoccer dedicated server segfaults on startup |
| jc2server | SteamCMD app 261140 installs no Linux-compatible dedicated server binary (openjc2-server not present) |
| jc3server | SteamCMD app 619960 installs no Linux-compatible dedicated server binary (executable file not found) |
| jk2server | JK2 download URL returns 404 |
| kfserver | SteamCMD app 215360 requires authentication (No subscription) |
| l4d2server | SteamCMD app 222860 returns Invalid platform on Linux |
| lastoasisserver | SteamCMD download timeout; likely too large for automated CI testing |
| ndserver | Nuclear Dawn dedicated server install is incomplete; gameinfo.txt missing |
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
| scpslserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| seserver | SteamCMD app 298740 installs no Linux-compatible dedicated server binary (executable file not found) |
| sfcserver | SourceForts Classic install incomplete; sfclassic/gameinfo.txt missing |
| skyrimtogetherrebornserver | TiltedEvolution has no GitHub release assets |
| smallandserver | SteamCMD downloads successfully but server never outputs expected readiness markers |
| ss14server | SS14 CDN returns 404 |
| starbound | SteamCMD app 211820 installs no Linux-compatible dedicated server binary (linux64/starbound_server not present) |
| stationeersserver | Can't start server that is already running (process management issue during setup) |
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

## SKIPPED (86)

Tests with `pytest.mark.skip` or a `require_proton()` / `require_command()` guard — need a prerequisite before they can run.

| Test | Skip reason |
|------|-------------|
| stormworksserver | Requires Wine or Proton-GE; Windows binary (server64.exe) via SteamCMD app 1247090; run scripts/install_proton.sh |
| arksurvivalascended | Requires Wine or Proton-GE; Windows binary (ArkAscendedServer.exe) via SteamCMD app 2430930; run scripts/install_proton.sh |
| askaserver | Requires Wine or Proton-GE; Windows binary (AskaServer.exe) via SteamCMD app 3246670; run scripts/install_proton.sh |
| astroneerserver | Requires Wine or Proton-GE; Windows binary (AstroServer.exe) via SteamCMD app 728470; run scripts/install_proton.sh |
| blackops3server | Requires Wine or Proton-GE; Windows binary (UnrankedServer/Launch_Server.bat) via SteamCMD app 545990; run scripts/install_proton.sh |
| blackwakeserver | Requires Wine or Proton-GE; Windows binary (BlackwakeServer.exe) via SteamCMD app 423410; run scripts/install_proton.sh |
| darkandlightserver | Requires Wine or Proton-GE; Windows binary (DNLServer.exe) via SteamCMD app 630230; run scripts/install_proton.sh |
| ducksideserver | Requires Wine or Proton-GE; Windows binary (DucksideServer.exe) via SteamCMD app 2690320; run scripts/install_proton.sh |
| empyrionserver | Requires Wine or Proton-GE; Windows binary (EmpyrionLauncher.exe) via SteamCMD app 530870; run scripts/install_proton.sh |
| fearthenightserver | Requires Wine or Proton-GE; Windows binary (MoonlightServer.exe) via SteamCMD app 764940; run scripts/install_proton.sh |
| groundbranchserver | Requires Wine or Proton-GE; Windows binary (GroundBranch/Binaries/Win64/GroundBranchServer-Win64-Shipping.exe) via SteamCMD app 476400; run scripts/install_proton.sh |
| heatserver | Requires Wine or Proton-GE; Windows binary (HeatServer.exe) via SteamCMD app 996600; run scripts/install_proton.sh |
| hellletlooseserver | Requires Wine or Proton-GE; Windows binary (HLLServer.exe) via SteamCMD app 822500; run scripts/install_proton.sh |
| icarusserver | Requires Wine or Proton-GE; Windows binary (IcarusServer.exe) via SteamCMD app 2089300; run scripts/install_proton.sh |
| lifeisfeudalserver | Requires Wine or Proton-GE; Windows binary (ddctd_cm_yo_server.exe) via SteamCMD app 320850; run scripts/install_proton.sh |
| medievalengineersserver | Requires Wine or Proton-GE; Windows binary (MedievalEngineersDedicated.exe) via SteamCMD app 367970; run scripts/install_proton.sh |
| miscreatedserver | Requires Wine or Proton-GE; Windows binary (MiscreatedServer.exe) via SteamCMD app 302200; run scripts/install_proton.sh |
| motortownserver | Requires Wine or Proton-GE; Windows binary (MotorTownServer-Win64-Shipping.exe) via SteamCMD app 2223650; run scripts/install_proton.sh |
| mw3server | Requires Wine or Proton-GE; Windows binary (iw5mp_server.exe) via SteamCMD app 115310; run scripts/install_proton.sh |
| noonesurvivedserver | Requires Wine or Proton-GE; Windows binary (WRSHServer.exe) via SteamCMD app 2329680; run scripts/install_proton.sh |
| notdserver | Requires Wine or Proton-GE; Windows binary (LFServer.exe) via SteamCMD app 1420710; run scripts/install_proton.sh |
| outpostzeroserver | Requires Wine or Proton-GE; Windows binary (WindowsServer/SurvivalGameServer.exe) via SteamCMD app 762880; run scripts/install_proton.sh |
| pixarkserver | Requires Wine or Proton-GE; Windows binary (ShooterGame/Binaries/Win64/PixARKServer.exe) via SteamCMD app 824360; run scripts/install_proton.sh |
| primalcarnageextinctionserver | Requires Wine or Proton-GE; Windows binary (Binaries/Win64/PrimalCarnageServer.exe) via SteamCMD app 336400; run scripts/install_proton.sh |
| readyornotserver | Requires Wine or Proton-GE; Windows binary (ReadyOrNotServer.exe) via SteamCMD app 950290; run scripts/install_proton.sh |
| reignofkingsserver | Requires Wine or Proton-GE; Windows binary (Server.exe) via SteamCMD app 381690; run scripts/install_proton.sh |
| remnantsserver | Requires Wine or Proton-GE; Windows binary (StartServer.bat) via SteamCMD app 1141420; run scripts/install_proton.sh |
| returntomoriaserver | Requires Wine or Proton-GE; Windows binary (MoriaServer.exe) via SteamCMD app 3349480; run scripts/install_proton.sh |
| ror2server | Requires Wine or Proton-GE; Windows binary (Risk of Rain 2.exe) via SteamCMD app 1180760; run scripts/install_proton.sh |
| rs2server | Requires Wine or Proton-GE; Windows binary (VNGame.exe) via SteamCMD app 418480; run scripts/install_proton.sh |
| saleblazersserver | Requires Wine or Proton-GE; Windows binary (Saleblazers.exe) via SteamCMD app 3099600; run scripts/install_proton.sh |
| scumserver | Requires Wine or Proton-GE; Windows binary (SCUMServer.exe) via SteamCMD app 3792580; run scripts/install_proton.sh |
| sniperelite4server | Requires Wine or Proton-GE; Windows binary (bin/SniperElite4_Dedicated.exe) via SteamCMD app 568880; run scripts/install_proton.sh |
| sonsoftheforestserver | Requires Wine or Proton-GE; Windows binary (StartSOTFDedicated.bat) via SteamCMD app 2465200; run scripts/install_proton.sh |
| starruptureserver | Requires Wine or Proton-GE; Windows binary (StarRuptureServerEOS.exe) via SteamCMD app 3809400; run scripts/install_proton.sh |
| staxelserver | Requires Wine or Proton-GE; Windows binary (Staxel.ServerWizard.exe) via SteamCMD app 755170; run scripts/install_proton.sh |
| subsistenceserver | Requires Wine or Proton-GE; Windows binary (run_dedicated_server.bat) via SteamCMD app 1362640; run scripts/install_proton.sh |
| terratechworldsserver | Requires Wine or Proton-GE; Windows binary (TT2Server.exe) via SteamCMD app 2533070; run scripts/install_proton.sh |
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