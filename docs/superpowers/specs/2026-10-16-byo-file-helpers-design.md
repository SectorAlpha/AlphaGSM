# Game-specific BYO file helpers

## Scope

Add game-specific recipes that understand which operator-supplied files each
BYO server needs, where those files come from, and where they belong. Generic
file-existence helpers alone do not meet the user's requirement.

The user has no Steam installation and can currently verify only on
Linux. Validation therefore uses temporary files and mocked lifecycle
dependencies; it must not download games, install Steam, or claim real game
startup or Windows support has been verified.

## Approach

Use the `get_asset_requirements(server)` interface and local asset importer
currently present in the workspace. Preserve that existing work and avoid a
competing recipe format. Each game module owns its recipe, preferably beside
its implementation; shared code handles inspection and reports.

Extend recipes with acquisition metadata describing:

- the exact mandatory files, allowed alternatives/globs where necessary,
  optional files, and complete content trees that must be retained;
- source kind: owned installation, client export, official release/archive,
  operator-supplied archive, or provider-generated configuration;
- source-relative paths and practical acquisition steps, with authoritative
  documentation or release links; a release page is guidance, not a direct
  download artifact;
- the destination relative to the instance install root, or an explicitly
  configured external game-install location;
- platform/build applicability and whether only a known sentinel or a fuller
  file set can currently be checked.

Resolve configuration-dependent paths using the instance's settings, including
`exe_name`, ETS2/ATS `configdir`, and DST cluster/shard settings. Use explicit
source paths supplied by the operator; having Steam installed is not required
to inspect a recipe or import an already-exported archive.

Asset checks and missing-file errors should report what is missing, where it
belongs, and how to obtain it. Keep the existing standard BYO support wording.
Do not fabricate a download URL or claim that a launcher/sentinel proves a
complete usable server. Preserve existing game-specific validators for archive
members, JSON structure, tokens, and other richer requirements.

Requirement reporting must not implicitly enable managed import for a recipe
that the current importer cannot safely express. Keep unsupported import paths
explicit, and retain manual steps for credentials or complex multi-source
payloads. Acquisition instructions do not trigger downloads or Steam installs.

### Authenticated SteamCMD acquisition

Treat authenticated SteamCMD as an acquisition route when the account can
access the required app/depot content. A game recipe should describe the
source app ID, branch, requested platform, authentication requirement, and
which downloaded files satisfy its asset requirements. Dedicated-server and
base-game app IDs may differ; do not assume logging into the dedicated app
will download missing client content automatically.

The user approved authenticated SteamCMD as an alternative way to obtain the
required files and then explicitly requested secure auth storage. Implement a
small managed session-profile flow alongside the recipes. The current
`_get_login_args` helper reads shared username/password settings, but the new
flow must not retain an account password or pass it in argv. Recipes contain
authentication requirements and profile references, never credential values.

Store each profile in an owner-only directory under the AlphaGSM state root.
Record the username and a separate SteamCMD runtime/session directory. Use
0700 directories and remove group/other file permissions on Linux; reject
symlinks, unexpected ownership, and unsafe profile names. Login delegates
password and Steam Guard prompts to interactive SteamCMD without capturing
the credential exchange. Later downloads use the cached session with no
password argument, fail fast when reauthentication is required, and never
silently downgrade an authenticated recipe to anonymous login. Session files
are credentials: do not include them in server trees, asset exports, backups,
images, normal status output, or test evidence. Status reports only local
profile state, not an unverified claim that Valve will accept the login.

Add `alphagsm steam-auth login PROFILE USERNAME`, `status PROFILE`, and
`logout PROFILE`. Logout removes only the selected local cached session; it
does not claim server-side revocation. Current host-side SteamCMD support is
Linux-only, so fail clearly on unsupported hosts rather than claiming file
permissions alone protect credentials on Windows. No OS-keyring dependency or
password-retention feature is needed for the session-only design.

Download an authorized app into isolated temporary staging, validate and import
only allowlisted recipe files, and remove staging on success or failure.
SteamCMD app/depot downloads can contain more than the selected files; do not
claim that only the required bytes are transferred. Keep existing importer
ownership and rollback protections. Acquisition is an explicit operator action,
not a side effect of a read-only asset check.

SteamCMD on Linux can request Windows payloads through the existing platform
override. Obtaining those files does not establish that the server can run on
Linux, and native Windows runtime validation remains outstanding. Preserve
the existing Wine/Proton runtime contract where applicable.

Authentication does not generate ETS2/ATS client exports, Klei cluster tokens,
ATLAS grid exports, or other game-specific runtime credentials. Keep those
requirements explicit. Do not change an AUTH/BYO support state until its real
install and lifecycle are validated with an appropriately entitled account.

No Steam credentials are available for validation in this task. Unit tests
may prove acquisition selection and expected SteamCMD arguments using mocks;
they must not be reported as proof of entitlement, successful login/download,
or real game readiness.

Use platform-neutral path handling for recipes and synthetic tests. Record
Windows-only source/build requirements explicitly rather than substituting
Linux binaries. Native Windows behavior remains unverified on this host.

## Adoption

Cover every current file-based BYO module, not only the original proposed
five GoldSrc mods and ETS2. Authentication/service-only requirements must be
identified as such rather than assigned imaginary file recipes. Preserve
provider requirement metadata for mixed authentication/staged-file paths.

The following inventory records the existing repository's starting contracts.
Executable/map sentinels are not complete dependency lists. Before a production
recipe is accepted, audit companion content and record an authoritative source
or an explicit unavailable/manual-source condition.

| Module | Existing files/layout to understand | Acquisition route to describe |
| --- | --- | --- |
| codserver | `main/*.pk3` containing the configured `maps/mp/<map>.bsp` | Owned Call of Duty multiplayer installation; dedicated archive alone lacks map data |
| cod2server | `main/localized_*.iwd`, `main/default_localize_mp.cfg` | Owned Call of Duty 2 `main/` directory |
| cod4server | `fileSysCheck.cfg`, `main/localized_*.iwd` | Owned Call of Duty 4 installation |
| coduoserver | `main/pak0.pk3` or `main/default_mp.cfg` | Owned base Call of Duty installation, alongside United Offensive server files |
| aloftserver | Server tree containing `AloftServerNoGuiLoad.ps1` | Operator's Aloft dedicated server installation; audit Windows payload applicability |
| ahlserver | Complete `action/` tree; `maps/ahl_hydro.bsp` sentinel | Action Half-Life distribution or existing mod installation |
| alienarenaserver | Native server tree with `crx-dedicated` and game data | Alien Arena server distribution or existing native installation |
| bf1942server | Linux dedicated tree with `bf1942_lnxded` | Operator-supplied compatible server archive; verify availability of legacy sources |
| bbserver | Complete `brainbread/`; `maps/bb_chp4_slaywatch.bsp` | BrainBread distribution or existing mod installation |
| bfvserver | Linux dedicated tree with `bfvietnam_lnxded` | Operator-supplied compatible server archive; distinguish download page from payload |
| dstserver | `<confdir>/<cluster>/cluster_token.txt`, `cluster.ini`, `<shard>/server.ini` | Klei-generated token plus operator-created/exported cluster configuration; keep secrets out of reports |
| atlasserver | `ShooterGame/ServerGrid.json`, `ServerGrid.ServerOnly.json`, populated `ServerGrid/` | Official ServerGridEditor export; preserve server-only secrets |
| etlegacyserver | `etmain/pak0.pk3`; optional `pak1.pk3`, `pak2.pk3` for other mods | Original Wolfenstein: Enemy Territory installation or upstream-documented game-data download |
| ets2server | Nonempty `server_packages.sii`, `server_packages.dat` in configured game home | Run `export_server_packages` in an owned ETS2 client with a loaded map |
| atsserver | Exported `server_packages.sii`, `server_packages.dat` in configured game home | Run `export_server_packages` in an owned ATS client with a loaded map |
| foundryserver | Native tree with `FoundryDedicatedServer` and companion data | Operator's matching FOUNDRY dedicated server distribution; verify platform availability |
| goldeneyesourceserver | Complete Source 2007/AppID 310 base plus top-level `gesource/` | Existing complete server tree or official GoldenEye: Source distribution; retain documented source-access failures |
| gravserver | Dedicated tree with configured `CAGGameServer-Win32-Shipping` payload | Operator's GRAV server installation; audit actual filename and platform layout |
| hogwarpserver | Complete Windows server tree with `HogWarpServer.exe` | Official HogWarp server distribution or operator-supplied archive; document access requirements |
| identityserver | Server tree with `IdentityServer.x86_64` | Operator-supplied Identity server archive or existing install; report unavailable upstream artifacts honestly |
| jk2server | Linux server tree with `jk2mvded.x86_64` and needed game data | Compatible Jedi Outcast server release plus owned base content; audit build compatibility |
| minecraft.custom | Configured server JAR and its distribution-specific companions | Operator's chosen server project/distribution; use a specific release rather than guessing a universal source |
| minecraft.tekkit | Matching Tekkit server pack with `Tekkit.jar` | Selected official Technic pack's server distribution; distinguish Tekkit variants |
| mxbikesserver | Dedicated archive with configured executable and data | Official MX Bikes dedicated-server distribution or supplied archive; verify platform |
| ndserver | Complete `nucleardawn/`; `maps/hydro.bsp` sentinel | Complete Nuclear Dawn game/server content rather than the partial anonymous payload |
| nsserver | Complete `ns/`; `maps/ns_hera.bsp` sentinel | Natural Selection distribution or existing mod installation |
| q3server | `baseq3/pak0.pk3` plus applicable patch data | Owned Quake III Arena installation; engine binaries are a separate distribution |
| q4server | Linux dedicated server with `q4ded.x86` plus required `q4base/` data | Compatible server distribution plus owned Quake 4 data; do not present the known dead archive as working |
| rtcwserver | `main/mp_bin.pk3`, `mp_pak0` through `mp_pak5`, `mp_pakmaps0` through `mp_pakmaps6` | Original RTCW multiplayer `Main/` plus upstream patch-data archive |
| mohaaserver | Dedicated tree with `mohaa_lnxded` and game data | Owned Medal of Honor: Allied Assault content plus compatible Linux dedicated payload |
| sampserver | Dedicated tree with `samp03svr` and supporting data | Compatible SA-MP server distribution or operator-supplied archive; verify legacy availability |
| skyrimtogetherrebornserver | Matching tree with `SkyrimTogetherServer` | Official TiltedEvolution/Skyrim Together Reborn server release |
| ss14server | Complete Linux x64 distribution with `Robust.Server` | Chosen fork's compatible server build/archive; account for unavailable Wizard's Den builds |
| sfcserver | Complete `sfclassic/`; `maps/sf_astrodome.bsp` sentinel | Official SourceForts Classic full-version ModDB distribution |
| starbound | Native `linux64/starbound_server` with companion assets | Owned Starbound installation/server tree; include game assets rather than only the executable |
| sof2server | Dedicated tree with `sof2ded` and base game data | Owned Soldier of Fortune II content plus compatible Linux dedicated payload |
| stormworksserver | Authenticated server installation with `server64.exe` and data | Steam/SteamCMD-authenticated Dedicated Server tool; preserve provider-auth requirement |
| subnauticaserver | Owned Subnautica installation configured for Nitrox | Matching owned game installation plus official Nitrox distribution; audit required game build |
| tsserver | Complete `ts/`; `maps/ts_neobaroque.bsp` sentinel | The Specialists distribution or existing mod installation |
| ut3server | Dedicated tree with `Binaries/ut3`, `UTGame/`, and companions | Owned UT3 content and compatible Linux dedicated-server distribution |
| vsserver | Complete `vs/`; `maps/vs_frost.bsp` sentinel | Vampire Slayer distribution or existing mod installation |
| zmrserver | Complete `zombie_master_reborn/`; `maps/zm_docksofthedead.bsp` sentinel | Official Zombie Master: Reborn content release or complete existing installation |

The remaining current BYO rows are Astroneer's routable registration endpoint,
Quake Live's authenticated entitlement/configuration, and Life is Feudal's
database service. Report those prerequisites through their existing contracts;
do not suggest that importing a file satisfies them.

The in-progress Project Reclaimer recipe is existing workspace work and must
be preserved. Any metadata extension must remain backward-compatible with it.

## Verification and documentation

Write a coverage test ensuring every current file-based BYO module declares a
recipe with actionable source metadata and destination information. Test each
recipe with synthetic files, including absent files, wrong layouts, empty
exports, allowed alternatives/globs, and configured paths. Preserve the
existing importer's traversal, ownership, and rollback guarantees and test
source guidance without making network requests. Public archives and provider
credentials must never be fabricated to make a test pass.

Run focused tests, the unit suite, and the repository lint gate as available.
Do not run game integration or smoke lifecycle tests without the operator's
required assets. Record the Linux-only verification and outstanding real-game
and Windows validation explicitly. Update developer documentation, affected
server guides, and changelog. Do not promote support tracker states on the
strength of synthetic fixtures.

## Initial upstream source checks

- [SCS dedicated-server documentation](https://modding.scssoft.com/wiki/Documentation/Tools/Dedicated_Server)
  describes both exported package files, the export command, and copying them
  to the server home directory. It says additional DLC/mod data is unnecessary.
- [ET: Legacy's upstream FAQ](https://github.com/etlegacy/etlegacy/wiki/FAQ)
  distinguishes the original game data from engine releases and describes
  both copying an existing installation and obtaining the original free game.
- [iortcw's upstream README](https://github.com/iortcw/iortcw/blob/master/README.md)
  lists the RTCW multiplayer PK3 files and separate patch-data archive.
- [ioquake3's player guide](https://ioquake3.org/help/players-guide/)
  identifies owned Steam, GOG, and CD-ROM installations as sources for the
  original `baseq3/pak0.pk3`.
- [Valve's dedicated-server distribution documentation](https://partner.steamgames.com/doc/sdk/uploading/distributing_gs?l=english)
  explains anonymous package availability, while its
  [SteamCMD session instructions](https://partner.steamgames.com/doc/sdk/uploading?l=english)
  describe initial authentication and preserving login state.

These checks establish acquisition guidance for those examples, not successful
downloads or server readiness. Audit the remaining upstream instructions during
implementation before recording a source as verified.
