# Anonymous Steam Workshop server content

This matrix tracks game-specific Workshop activation through AlphaGSM. Anonymous dedicated-server installation alone does not prove Workshop access. A passing load result requires actual engine map, package, registry or mod execution evidence and the normal AlphaGSM lifecycle in each listed runtime.

Items and collections use numeric IDs or official Steam Community Workshop URLs. Every member must belong to the server's game AppID. Only public, dedicated-server-compatible content is in this campaign's scope; operator credentials and owned-assets hosting paths are excluded.

| Game | Workshop AppID | Anonymous content access | Process load | Docker load |
| --- | ---: | --- | --- | --- |
| Left 4 Dead 2 | 550 | Verified | Passed | Passed |
| Garry's Mod | 4000 | Verified | Passed | Passed |
| Unturned | 304930 | Verified | Passed | Passed |
| Project Zomboid | 108600 | Verified | Passed | Passed |
| Barotrauma | 602960 | Verified | Passed | Passed |
| Avorion | 445220 | Verified | Passed | Passed |
| Insurgency (2014) | 222880 | Verified native item and collection downloads | Passed | Passed |
| Day of Infamy | 447820 | Verified native item download | Passed | Passed |
| Conan Exiles | 440900 | Verified | Passed | Passed |
| ARK: Survival Evolved | 346110 | Verified | In progress | In progress |
| Squad | 393380 | Verified | Passed | Awaiting SSD Docker endpoint |
| Squad 44 | 736220 | Verified | In progress | In progress |
| Colony Survival | 366090 | Blocked: missing Workshop decryption key | Not validated | Not validated |
| No More Room in Hell | 224260 | Verified | Passed | Awaiting SSD Docker endpoint |
| BrainBread 2 | 346330 | Verified | Passed | Awaiting SSD Docker endpoint |
| Team Fortress 2 | 440 | Verified native map download without GSLT | Passed | Awaiting SSD Docker endpoint |
| Killing Floor 2 | 232090 | Verified map download | In progress | Awaiting SSD Docker endpoint |
| Rising Storm 2: Vietnam | 418460 | Verified map download | In progress | Awaiting SSD Docker endpoint |
| Natural Selection 2 | 4920 | Verified map and server-plugin downloads | In progress | Awaiting SSD Docker endpoint |
| Terraria tModLoader | 1281930 | Verified | Passed | Passed |
| rFactor 2 | 365960 | Verified free Studio 397 package | In progress | Awaiting SSD Docker endpoint |
| Alien Swarm: Reactive Drop | 563560 | Native loader documented; validation pending | Pending | Pending |
| Space Engineers | 244850 | Verified | In progress | In progress |
| Wreckfest | 228380 | Verified | In progress | In progress |
| Stationeers | 544550 | Verified | Passed | Awaiting SSD Docker endpoint |

## Fixture evidence and limitations

- L4D2: Back To School collection `121115793` and Admin System `214630948`; fresh engine load order enumerates all 11 VPKs, and Admin System execution was observed. Unavailable original collection `3819008159` is not a passing fixture.
- Garry's Mod: ULib/ULX collection `2886432224`; fresh native VFS CRCs and both live Lua APIs.
- Unturned: PEI Arena `2396897717`; native map loading and real A2S map identity.
- Project Zomboid: PrintIngameTimeOneHour `2773478544` on Build 42.21; native readiness, exact mod identity and server Lua execution. Build 41 has unit metadata coverage only.
- Barotrauma: BaroCraftables `2499918466`; enabled package hashes and its Welding Table prefab in the native registry. Docker console input uses a contained terminal relay.
- Avorion: AzimuthLib `1722652757`; its Lua `getInt` function executes in the running server and returns `42`.
- Insurgency: Amber Spirits Coop `498253639`, including public collection `552903640`; fresh native Workshop mounts and exact A2S map identity. No Steam Web API key is used.
- Day of Infamy: Stalingrad map; fresh native Workshop mount and exact A2S map identity.
- Conan Exiles: Enhanced Storage Reach `3733835102`; native PAK mount and its active Blueprint execution. Cleanup is followed by a fresh empty-list restart proving deactivation. Engine-generated unpacking caches are retained.
- Squad: ModLoader `3516838562`; fresh native PAK/IoStore mounting, mod serialization and layer registration. Native RCON confirms real population and loaded map/layer; cleanup and a fresh restart prove deactivation. The process lifecycle passed; its existing stop fallback required forced termination.
- No More Room in Hell: Mines of Moria `3514998402`; real A2S map identity `nmo_lotr_mines_of_moria_v3`, normal engine shutdown and managed asset cleanup in the process runtime.
- BrainBread 2: Frozen Heart `710060895`; the vendor's existing per-item Workshop search path loads `bbc_frozenheart`, confirmed by real A2S, followed by normal shutdown and cleanup in the process runtime.
- Team Fortress 2: Orange X3 `454299390`; fresh native `workshop/cp_orange_x3.ugc454299390` startup and A2S map `cp_orange_x3`, with no Steam account or GSLT. The process lifecycle and managed configuration cleanup passed; existing stop timeout required forced termination.
- tModLoader: Census `2687866031` on release `v2026.08.3.0`; fresh `TownProgress` command output from the actual loaded mod, native Terraria handshake and shutdown verification in both runtimes. Baseline lifecycles also passed.
- Stationeers: Mars Abandoned Frontier `3779655608`; a fresh native save contains its exact `AbandonedMars` world identity and loaded Structure prefabs. Native query/info, shutdown and removal of the managed mod configuration passed in the process runtime.
- rFactor 2: free Studio 397 Kart Cup `922034231` and AtlantaMP `917386837` download anonymously and install through the vendor's ModMgr. The dedicated engine refuses to start without an additional race-event package; package installation alone is not an engine-load pass.
- Colony Survival: three public items (`2904408335`, `1923512334`, `3708370627`) could not be downloaded anonymously. Steam reports a missing decryption key for inspected item manifests. Dedicated app `748090` installs anonymously; this does not establish content access. No native adapter is exposed for this blocked path.

Lifecycle success and port closure do not by themselves establish graceful save completion. Existing timeout/kill fallbacks occurred in some validated runs, including Conan Exiles and the Insurgency/Day of Infamy cases. Match each server guide's recorded limitations.

Remaining Docker validation is held until an SSD-backed Docker endpoint is available. The attempted host rootless daemon requires the missing `newuidmap` and `newgidmap` helpers from the `uidmap` system package. Large server files, Workshop caches and test logs already use the SSD. No pending Docker row represents a passing load result.

DST, Arma 3, DayZ, Starbound and Stormworks remain outside this no-auth campaign. CS2 public hosting has an account-bound GSLT requirement; its existing generic staging commands do not establish no-credential public hosting or arbitrary Workshop-map activation.
