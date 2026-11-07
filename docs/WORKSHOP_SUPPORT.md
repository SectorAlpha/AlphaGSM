# Anonymous Steam Workshop server content

This matrix tracks game-specific Workshop activation through AlphaGSM. Anonymous dedicated-server installation alone does not prove Workshop access. A passing load result requires actual engine map, package, registry or mod execution evidence and the normal AlphaGSM lifecycle in each listed runtime.

Items and collections use numeric IDs or official Steam Community Workshop URLs. Every member must belong to the server's game AppID. Only public, dedicated-server-compatible content is in this campaign's scope; operator credentials and owned-assets hosting paths are excluded.

CI now enables all 21 existing public anonymous Workshop integration suites,
their smoke scenarios and isolated rechecks. Required cases must run: a skip
fails CI. Each integration suite selects its explicit process or Docker lane;
local runs retain download opt-ins. Run
[`38775144746`](https://github.com/SectorAlpha/AlphaGSM/actions/runs/38775144746)
on PR head `6a446839` passed all 21 required Workshop integration suites in both
runtimes and their smoke scenarios. Separate unresolved candidates remain
identified in the matrix below.

The CI wrapper also supplies the existing public fixtures for Reactive Drop,
BrainBread 2, Day of Infamy, Garry's Mod, Insurgency, No More Room in Hell,
Natural Selection 2 and TF2 smoke runners, whose item/collection variables are
separate from their opt-in flags. Explicit fixture overrides are preserved.
Earlier stock-only smoke results for those runners are not Workshop evidence.

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
| ARK: Survival Evolved | 346110 | Verified | Passed | Passed |
| Squad | 393380 | Verified | Passed | Passed |
| Squad 44 | 736220 | Verified | Passed | Passed |
| Colony Survival | 366090 | Blocked: missing Workshop decryption key | Not validated | Not validated |
| No More Room in Hell | 224260 | Verified | Passed | Passed |
| BrainBread 2 | 346330 | Verified | Passed | Passed |
| Team Fortress 2 | 440 | Verified native map download without GSLT | Passed | Passed |
| Killing Floor 2 | 232090 | Verified map download | In progress | Awaiting SSD Docker endpoint |
| Rising Storm 2: Vietnam | 418460 | Verified map download | In progress | Awaiting SSD Docker endpoint |
| Natural Selection 2 | 4920 | Verified map and server-plugin downloads | Passed | Passed |
| Terraria tModLoader | 1281930 | Verified | Passed | Passed |
| rFactor 2 | 365960 | Verified free Studio 397 package | In progress | Awaiting SSD Docker endpoint |
| Alien Swarm: Reactive Drop | 563560 | Verified | Passed | Passed |
| Space Engineers | 244850 | Verified | Passed | Passed |
| Wreckfest | 228380 | Verified | Passed | Passed |
| Stationeers | 544550 | Verified | Passed | Passed |

## Fixture evidence and limitations

- ARK: Very Flat Map `2041231763` replaces the unsupported Linux `GetAll`
  introspection probe. Run `38702811625` passes metadata/decompression but the
  Linux-cooked branch crashes in native `LinkerLoad`. The adapter now follows
  [ARK Server Tools](https://github.com/arkmanager/ark-server-tools/blob/master/tools/arkmanager)
  and selects Windows-cooked content for the native Linux server. Both runtime
  integrations and Docker smoke passed in run `38748333313`, with fresh custom
  world startup and real A2S agreeing on `FlatMap`.
- Space Engineers' Docker smoke and both baseline/native integrations passed
  MES script execution in CI run `38649280824`. Process startup progressed
  beyond the VC prerequisite check but still exited before readiness in run
  `38702811625`, despite matching the container's virtual display. New Wine traces
  show a missing current-user LocalLow directory. Fresh template copies now allow
  normal Wine profile initialization. Process and Docker baseline/native MES
  integrations passed in run `38748333313`, requiring `Game ready` and the mod's
  own session-script initialization evidence.
- NS2's process and Docker native Workshop integrations passed in run
  `38655040006`, including the Docker authenticated loopback admin transport,
  exact native map origin, map-change execution, real A2S and shutdown.
- Wreckfest's process and Docker native Workshop integrations passed in run
  `38748333313`, after one real initialization lifecycle for a fresh engine profile.
  Both require the exact `crazy_2000_classic` native registry row and complete
  shutdown. Docker Workshop smoke passed in
  [run `38775144746`](https://github.com/SectorAlpha/AlphaGSM/actions/runs/38775144746/job/116564198854),
  including the fresh registry assertion, query/info, shutdown and cleanup.
- Squad 44's Ramelle `2387944294` native Workshop integration passed in both
  runtimes in run `38655040006`, together with Docker Workshop smoke. Checks
  require exact staged Workshop/SDK identity, native PAK precacher registration,
  successful mod serialization, constructed `Ramelle_Offensive_01` world and
  matching real A2S metadata, followed by shutdown. Stop retains its existing
  forced-stop fallback; graceful saving is not established.
- Reactive Drop's native Workshop integration passed in both runtimes in run
  `38748333313`, beyond its previously validated stock baseline.
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
- Team Fortress 2: Orange X3 `454299390`; process and Docker native integration
  passed in run `38748333313`, requiring fresh ready/current canonical
  `workshop/cp_orange_x3.ugc454299390` frames and real A2S. Screen Workshop smoke
  passed in [run `38775144746`](https://github.com/SectorAlpha/AlphaGSM/actions/runs/38775144746/job/116564198683),
  including bounded fresh response capture, native ready/current-map proof,
  real A2S, shutdown and cleanup.
  No Steam account or GSLT is used; existing stop fallbacks remain documented.
- tModLoader: Census `2687866031` on release `v2026.08.3.0`; fresh `TownProgress` command output from the actual loaded mod, native Terraria handshake and shutdown verification in both runtimes. Baseline lifecycles also passed.
- Stationeers: Mars Abandoned Frontier `3779655608`; a fresh native save contains its exact `AbandonedMars` world identity and loaded Structure prefabs. Native query/info, shutdown and removal of the managed mod configuration passed in the process runtime.
- rFactor 2: free Studio 397 Kart Cup `922034231` and AtlantaMP `917386837` download anonymously and install through the vendor's ModMgr. The dedicated engine refuses to start without an additional race-event package; package installation alone is not an engine-load pass.
- Colony Survival: three public items (`2904408335`, `1923512334`, `3708370627`) could not be downloaded anonymously. Steam reports a missing decryption key for inspected item manifests. Dedicated app `748090` installs anonymously; this does not establish content access. No native adapter is exposed for this blocked path.

Lifecycle success and port closure do not by themselves establish graceful save completion. Existing timeout/kill fallbacks occurred in some validated runs, including Conan Exiles and the Insurgency/Day of Infamy cases. Match each server guide's recorded limitations.

Run `38775144746` retained passing native integration cases in both runtimes
and passing smoke scenarios for all 21 required anonymous Workshop suites.
The preceding run `38748333313` also passed those native integrations; its
Avorion Docker recovery on an isolated recheck remains historical flaky
evidence. Squad, NMRIH, BrainBread 2 and Stationeers have Docker proof beyond
their earlier process results. KF2, Rising Storm 2 and rFactor 2 retain their
separate unresolved limitations; Colony Survival's anonymous content download
remains blocked.
All replacement validation runs in GitHub CI; no local Docker testing is used.

DST, Arma 3, DayZ, Starbound and Stormworks remain outside this no-auth campaign. CS2 public hosting has an account-bound GSLT requirement; its existing generic staging commands do not establish no-credential public hosting or arbitrary Workshop-map activation.
