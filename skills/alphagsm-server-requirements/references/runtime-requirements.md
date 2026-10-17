# Locate requirements for the selected game

Use this as a discovery map, not a universal package list. Start with canonical
module/version and the effective runtime. Follow the module's installer and
launcher helpers; absent `host_dependencies` does not mean no prerequisites.
The [capability inventory](../../../src/server/module_capabilities.json) covers
canonical games/aliases but is a generated routing index, not a host readiness
report. The [guide index](../../../docs/README.md) routes each supported game.

## Requirement layers

| Layer | Inspect | Verify without installing |
| --- | --- | --- |
| Manager | executable/version, runtime or standalone installation, selected process backend, wrapper and Python requirements | executable/help, installed package metadata; standalone need not need host Python except wrapper-native commands |
| Installation | configure/install, shared downloader/installer, shell helpers, requirement includes and Make targets | configured tool paths, library/package status and version metadata; no setup probe |
| Game runtime | module platform/CPU hooks, `host_dependencies`, launch command, runtime family, Dockerfile/entrypoint | exact executable/version, local image ID/provenance, daemon OS, mount visibility and doctor findings |
| Provider/assets | provider hook/validation, selected setup branch, guide and AUTH/BYO trackers | presence privately plus actual asset tree/archive/service validity; do not report secrets |
| Game configuration | setup options, schema, port claims, game config, installed maps/worlds and EULA/license | supported settings, full IP/port set and required files; preserve explicit operator choices |
| Capacity/network | selected upstream version's guidance, install/archive size, available storage/RAM, bindings/query protocol | observed resource/claim/access checks; public reachability remains unverified until tested |

Docker game execution does not move installation into that game container.
[SteamCMD setup](../../../src/utils/steamcmd.py) still runs in the AlphaGSM
manager environment and currently uses the Linux client. Prefer the
[containerized manager](../../../docker/manager/Dockerfile) rather than installing
that toolchain on a host that lacks it. Verify what the manager actually supplies;
it is not guaranteed to include every custom game's build tool. The manager
Dockerfile supplies Java and SteamCMD libraries, but does not explicitly bundle
the SteamCMD client or a general compiler toolchain. A required client bootstrap
inside the manager is an ordinary step of the approved AlphaGSM recipe.

## Runtime family routing

Read [runtime defaults and normalization](../../../src/server/runtime.py), the
selected module wrappers and matching scaffold. Do not choose from game name
alone. The global backend and module preference determine the effective engine;
editing stored `runtime` values alone cannot guarantee Docker execution.

| Family | Repository scaffold | Selected-path checks |
| --- | --- | --- |
| java | [Dockerfile](../../../docker/java/Dockerfile) | Exact game/JAR version's Java major, bootstrap-time Java, configured javapath, EULA and memory flags; proxies and custom jars may differ |
| quake-linux | [Dockerfile](../../../docker/quake-linux/Dockerfile) | Native binary CPU/library compatibility, engine/game data, maps and query ports; compile-from-source installer tools when applicable |
| service-console | [Dockerfile](../../../docker/service-console/Dockerfile) | Actual console/service binary and module-declared libraries, license/data paths and ports |
| simple-tcp | [Dockerfile](../../../docker/simple-tcp/Dockerfile) | Actual service binary/library dependencies and TCP endpoint; a family name does not prove protocol health |
| steamcmd-linux | [Dockerfile](../../../docker/steamcmd-linux/Dockerfile) | Installer-side SteamCMD/platform/libraries/login, depot/app/build, installed launcher, Steam SDK links, game/query ports |
| wine-proton | [Dockerfile](../../../docker/wine-proton/Dockerfile) | Windows depot, installer-side SteamCMD, Wine/Proton version/prefix, module-specific xvfb/VC runtimes/.NET and real game protocol |

The Docker runtime supplies many game-process dependencies; doctor may skip
host checks for that reason. A skipped host check cannot prove installer-side
tools, provider inputs or custom payloads are present. On platforms where a
check is not implemented, retain `unknown` rather than reporting `present`.

## Concrete distinctions to preserve

- [Minecraft Vanilla](../../../src/gamemodules/minecraft/vanilla.py) derives
  Java requirements from the selected version; do not assume the family's
  default major fits every build. [Bedrock](../../../src/gamemodules/minecraft/bedrock.py)
  is a different native implementation, not a Java JAR.
- `tf2` resolves to [teamfortress2](../../../src/gamemodules/teamfortress2/main.py).
  Check the configured SteamCMD executable, not just PATH. Missing SteamCMD is
  installed by the shared download helper as part of the managed setup recipe.
  Steam client self-updates inside that workflow need no separate approval.
- [TShock](../../../src/gamemodules/terraria/tshock.py) and
  [Vintage Story](../../../src/gamemodules/vintagestoryserver/main.py) declare
  `dotnet` requirements; do not assume every Terraria variant needs Mono or
  Java. Inspect the actual executable and supported release's runtime version.
- [Quake II](../../../src/gamemodules/q2server/main.py) has a source-build setup
  path that invokes `make server game`; undeclared build tools must still be
  discovered from the source/Makefile. New external host tools need installation
  approval; build inputs inside repository images and managed workflows do not.
- [ASKA](../../../src/gamemodules/askaserver/main.py) declares a provider token;
  [The Isle](../../../src/gamemodules/tiserver/main.py) declares EOS credentials;
  [BattleBit](../../../src/gamemodules/battlebitserver/main.py) declares API
  provisioning. These are operator/provider inputs, not installable packages.
- [GoldenEye: Source](../../../src/gamemodules/goldeneyesourceserver/main.py)
  requires a complete operator-staged base plus game-content tree. Validate
  contents, not merely a URL/string. In contrast, do not invent an AUTH/BYO
  requirement for [Palworld](../../../src/gamemodules/palworld/main.py) or
  [Rising Storm 2](../../../src/gamemodules/rs2server/main.py) when the selected
  default path declares anonymous SteamCMD and current guides say PASSED.

For an unfamiliar module, follow the same discovery procedure rather than
extrapolating these examples. Identify the exact missing item, lifecycle phase,
location and source; hand off unresolved upstream requirements explicitly.

## Workshop-capable checkout distinctions

If `docs/WORKSHOP_SUPPORT.md` exists, inspect its separate anonymous-access,
process-load and Docker-load columns. Use [Workshop workflows](../../alphagsm-content-operations/references/workshop-workflows.md)
for staging versus native activation. Public visibility and anonymous server
installation do not guarantee anonymous content downloads or server compatibility.
Do not invent provider credentials for an unsupported anonymous download.

When `terraria.tmodloader` is present, inspect its own package and guide. It
installs the public GitHub release and its native launcher can download the
required .NET runtime on first startup. This is a managed installation step,
not a reason to pre-install host .NET or require Steam-client login. Workshop
uses its declared game AppID and compatible server-side TMOD format. Preserve
its Worlds/Saved/Mods/config paths and use the native Terraria handshake.

Use current protocol hooks for newly enabled servers. A module-owned local
RCON password/configuration, such as Squad's `squad_rcon` health path, is a
game setting/secret rather than provider Steam authentication. A transport-only
UDP hook, such as current Linux Wreckfest, provides limited reachability and
needs fresh native startup and runtime liveness; it cannot supply fabricated
map/player fields, an application response or a measured RTT.
