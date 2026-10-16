# Files supplied by the operator

Some servers need original game data, an exported client configuration, or a
complete server distribution that AlphaGSM cannot download anonymously. Each
file-based BYO module declares its own files, destinations and acquisition
instructions.

For an instance you have already created:

```bash
alphagsm myserver assets requirements
alphagsm myserver assets requirements --json
alphagsm myserver assets check
```

Requirements can be inspected before setup or login. Checks report whether
declared files exist with the spelling required by the host filesystem; they
do not start a server or prove game readiness. Source imports can accept
case variations declared by a recipe and normalize the published filenames.
The install selection aims for a complete dedicated server with the fullest
compatible content available from its declared source. Keep all compatible maps,
packages, scripts, required libraries and supporting data. The required-file
checks are minimum readiness checks, not a reason to discard other usable maps
or resources. Full client download staging is disposable; unrelated client
executables and rendering components do not belong in the installed server.
Game content archives stay intact so their maps and companion resources remain
available. Each validated game should leave a checked-in reusable installer or
import recipe that reproduces that result.

Manual distributions are marked `sentinel-only`: a map or executable can identify
a candidate tree, but cannot establish that all companion resources are present.
Follow the recipe's instructions for the complete compatible distribution.

## Preferred Steam-owned setup

For a managed recipe with a declared SteamCMD source, let AlphaGSM download the
owned files during setup on Linux:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm myserver setup --auth-profile owned
alphagsm myserver assets check
```

Enter the password and Steam Guard directly in SteamCMD's terminal prompts.
No desktop Steam installation is needed. The account must be entitled to the
source app and its content. Local session presence does not prove that access.
See [private session profiles](steamcmd-auth.md).

Setup remembers only the profile name for this server. Later setup runs reuse
it when required owned files are missing. Existing valid files avoid another
full-app download. To replace the name, pass another `--auth-profile`; to clear
it, run `alphagsm myserver set steam_auth_profile DELETE`.

To explicitly refresh the declared files without installing an engine:

```bash
alphagsm myserver assets fetch steam-owned --auth-profile owned
```

SteamCMD downloads an app/depot into disposable staging. AlphaGSM validates and
imports only the selected recipe files, then removes staging on success or
failure. It does not promise to download only those files over the network.
Setup and file acquisition do not start the game server.

## Use an existing Steam library instead

To copy the relevant files from a local Steam installation or library:

```bash
alphagsm myserver setup --steam-dir /path/to/Steam
alphagsm myserver setup --steam-dir /path/to/SteamLibrary/steamapps
```

The helper locates the recipe's declared AppID using local install manifests.
A Steam root can discover additional libraries; an explicit `steamapps` path
selects only that library. Multiple matching installations require a more
specific path. Steam and its installed files are read-only sources; only the
recipe's allowlisted files reach the server.

An explicit `--steam-dir` or `--assets` selects a local source for that run and
overrides a remembered profile. The three explicit source options cannot be
combined. An authentication/download failure never silently falls back to
local files or anonymous access.

## Import other existing files

Where the recipe supports managed import, supply a local game directory, ZIP,
or tar archive:

```bash
alphagsm myserver assets import /path/to/owned-game
alphagsm myserver setup --assets /path/to/owned-game
alphagsm myserver assets export /path/to/owned-game --output /path/to/assets.zip
```

The server must be stopped before file acquisition/import. Standalone asset
commands need an installation directory configured first; setup configures it
before its file phase. Imports record ownership and refuse to replace unrelated
or externally changed files. Selected content must satisfy the same game
requirements used by checks before publication or export.

Recipes without managed import, Steam source metadata or a known complete
layout keep their manual staging/export instructions. Steam login does not
replace client exports or provider-specific tokens. Setup without any source
selection or remembered profile keeps the existing module preparation flow.

The current `steam-owned` source declarations are:

| Module | Source app | Selected content |
| --- | --- | --- |
| `codserver` | Original Call of Duty, 2620 | `main/` PK3 data containing the configured multiplayer map |
| `cod2server` | Call of Duty 2, 2630 | `main/` IWD files and original localization config when present |
| `cod4server` | Original Call of Duty 4, 7940 | required config, `main/` IWD files and declared `zone/` fastfiles |
| `coduoserver` | Original Call of Duty, 2620 | base `main/` data; the expansion's `uo/` files are separate |
| `q3server` | Quake III Arena, 2200 | `baseq3/pak0.pk3` and applicable `pak1` through `pak8` data |
| `rtcwserver` | Return to Castle Wolfenstein, 9010 | declared multiplayer PK3 files, normalized into `main/` |

These source identities and file-selection paths have synthetic test coverage;
authenticated downloads and real game lifecycles have not been validated here.
Additional compatible patch files or content outside the allowlist may still
need manual staging. An owned Windows payload is not proof of Linux runtime
compatibility.

ETS2 and ATS need `server_packages.sii` and `server_packages.dat` generated by
`export_server_packages` in a running owned client. Authentication cannot
replace that export step. A relative `configdir` supports managed import into
the server installation. With an absolute `configdir`, stage both exports
manually in that home and use `assets check` to inspect them; managed import
and export are unavailable for that external-home configuration. Klei tokens,
ATLAS grid exports and game-server login tokens also retain their separate
preparation requirements.

## Local validation

Live authenticated tests require an entitled account or cached session. A
session is a credential. CI integration testing is deferred for this feature;
offline tests use synthetic files and fake SteamCMD processes.

When an operator is ready to log in, validate one game at a time in an isolated
scratch directory. Keep the private auth profile separate from the server
directory and exported assets. A successful file check establishes only the
declared file contract; use that game's normal readiness, query/info and stop
checks separately when validating its lifecycle.

Each game must answer a real native query on its configured game/query port
using the correct TCP/UDP protocol. Require running `status`, `query`, `info`
and `info --json`, then stopped status and verified process/listener shutdown.
Record the endpoint and probe scope. Fix and retest the game module or shared
query/configuration helper when these checks expose a defect; an open socket
or running process alone does not complete that game.

Quake III Arena was validated locally on 2026-10-16 through authenticated
setup, nine allowlisted PK3 files, repeat setup without Steam acquisition,
a dedicated engine payload with all 36 maps retained, native Quake UDP
query/info, and verified shutdown. Docker and the other
authenticated game sources remain untested in this local campaign.
