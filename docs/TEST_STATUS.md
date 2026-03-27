# Integration Test Status

Last updated: 2026-03-28

## Summary

| Status   | Count |
|----------|-------|
| PASSED   | 71    |
| DISABLED | 82    |
| SKIPPED  | 81    |
| RUNNABLE | 0     |

## Status Key

- **PASSED** — Test ran successfully in a prior session.
- **DISABLED** — Module is in `disabled_servers.conf`; known broken on Linux.
- **SKIPPED** — Test file has `pytest.mark.skip`; needs prerequisite work before it can run.
- **RUNNABLE** — Test exists and has no skip marker but has not been confirmed passing yet.

## PASSED (71)

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
| colserver | SteamCMD |
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
| groundbranchserver | SteamCMD (Proton) |
| mythofempiresserver | SteamCMD (Proton) |
| reignofdwarfserver | SteamCMD (Proton) |
| sunkenlandserver | SteamCMD (Proton) |
| theforestserver | SteamCMD (Proton) |
| askaserver | SteamCMD (Wine) |
| remnantsserver | SteamCMD (Wine) |
| readyornotserver | SteamCMD (Wine) |

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
| mw3server | SteamCMD app 115310 requires authentication (No subscription) |
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

## SKIPPED (81)

Tests with `pytest.mark.skip` or a `require_proton()` / `require_command()` guard — need a prerequisite before they can run.

| Test | Skip reason |
|------|-------------|
| stormworksserver | Wine: SteamCMD app 1247090 is now a redirect stub; server64.exe starts under Wine but produces no console output (redirect message appears in a Windows message box, not stdout); test waits full 300s before skipping |
| arksurvivalascended | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2430930 (ARK Survival Ascended) is extremely large — run individually with extended timeout |
| astroneerserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 728470 — run individually to verify |
| blackops3server | Requires Wine or Proton-GE; Windows binary (UnrankedServer/Launch_Server.bat) via SteamCMD app 545990; run scripts/install_proton.sh |
| blackwakeserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 423410 — run individually to verify |
| darkandlightserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 630230 — run individually to verify |
| ducksideserver | SteamCMD app 2690320 requires authentication (No subscription) |
| empyrionserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 530870 — run individually to verify |
| fearthenightserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 764940 — run individually to verify |
| heatserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 996600 — run individually to verify |
| hellletlooseserver | SteamCMD app 822500 requires authentication (No subscription) |
| icarusserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2089300 (Icarus) is very large — run individually with extended timeout |
| lifeisfeudalserver | Wine: server (ddctd_cm_yo_server.exe, app 320850) crashes immediately under Wine before writing log markers; stop command fails with "Can't stop a server that isn't running" |
| medievalengineersserver | Wine: server (MedievalEngineersDedicated.exe, app 367970) crashes immediately under Wine before writing log markers; stop command fails with "Can't stop a server that isn't running" |
| miscreatedserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 302200 — run individually to verify |
| motortownserver | SteamCMD app 2223650 requires authentication (No subscription) |
| noonesurvivedserver | Requires Wine or Proton-GE; Windows binary (WRSHServer.exe) via SteamCMD app 2329680; run scripts/install_proton.sh |
| notdserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 1420710 — run individually to verify |
| outpostzeroserver | Requires Wine or Proton-GE; Windows binary (WindowsServer/SurvivalGameServer.exe) via SteamCMD app 762880; run scripts/install_proton.sh |
| pixarkserver | Requires Wine or Proton-GE; Windows binary (ShooterGame/Binaries/Win64/PixARKServer.exe) via SteamCMD app 824360; run scripts/install_proton.sh |
| primalcarnageextinctionserver | Wine: server (PrimalCarnageServer.exe, app 336400) crashes immediately under Wine before writing log markers; stop command fails with "Can't stop a server that isn't running" |
| reignofkingsserver | SteamCMD app 381690 requires authentication (No subscription) |
| returntomoriaserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 3349480 — run individually to verify |
| ror2server | SteamCMD app 1180760 requires authentication (No subscription) |
| rs2server | Requires Wine or Proton-GE; Windows binary (VNGame.exe) via SteamCMD app 418480; run scripts/install_proton.sh |
| saleblazersserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 3099600 — run individually to verify |
| scumserver | Requires Wine or Proton-GE; Windows binary (SCUMServer.exe) via SteamCMD app 3792580; run scripts/install_proton.sh |
| sniperelite4server | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 568880 (Sniper Elite 4) is very large — run individually with extended timeout |
| sonsoftheforestserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2465200 (Sons of the Forest) is large — run individually with extended timeout |
| starruptureserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 3809400 — run individually to verify |
| staxelserver | SteamCMD app 755170 requires authentication (No subscription) |
| subsistenceserver | Wine: server (run_dedicated_server.bat, app 1362640) crashes immediately under Wine before writing log markers; stop command fails with "Can't stop a server that isn't running" |
| terratechworldsserver | Wine: SteamCMD download timed out (>20 min) during parallel testing; app 2533070 — run individually to verify |
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