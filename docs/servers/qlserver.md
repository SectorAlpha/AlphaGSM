# Quake Live

This guide covers the `qlserver` module in AlphaGSM.

`qlserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that owned/authenticated Quake Live
entitlement plus server-auth/config prerequisite, while local runs remain
process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myqlserver create qlserver
```

Run setup:

```bash
alphagsm myqlserver setup
```

Start it:

```bash
alphagsm myqlserver start
```

Check it:

```bash
alphagsm myqlserver status
```

Stop it:

```bash
alphagsm myqlserver stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- SteamCMD downloads the server files

Quake Live is supported in `ENABLED (BYO)` mode in
AlphaGSM. The anonymous dedicated payload installs, but the current Linux
server still exits immediately on startup unless the operator supplies the
missing upstream requirements.

In practice, treat the current requirement as:

- an owned/authenticated Quake Live Steam entitlement instead of anonymous-only
  SteamCMD setup
- any server-side Quake Live auth/config material your deployment requires

The current blocker is not a missing binary path. `qzeroded.x64` installs, but
anonymous startup is still not sufficient to reach a queryable dedicated
server. If you are testing this lane locally, start by authenticating the
Steam install/update flow with an owned account, then retry the normal
AlphaGSM lifecycle.

## Useful Commands

```bash
alphagsm myqlserver update
alphagsm myqlserver backup
alphagsm myqlserver set servername "AlphaGSM QL"
alphagsm myqlserver set map asylum
```

`set servername` and `set map` rewrite `baseq3/server.cfg` immediately through the schema-backed config-sync path.

## Mod Sources

Quake Live content management currently targets the directory that contains the
configured `servercfg` file. By default that is `baseq3/`, but if you point
`servercfg` at a custom relative path such as `custommod/server.cfg`, AlphaGSM
installs into that directory instead.

- Current mod source support is direct `url` entries only.
- `mod add url <https-url>` accepts direct `.pk3` URLs and supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload exposes either `<content-root>/<name>.pk3` or bare `.pk3` files at the archive root.
- `mod cleanup` removes only AlphaGSM-tracked `.pk3` files and keeps its cache/state under `.alphagsm/mods/qlserver/`.
- The first Quake Live slice intentionally stops at `.pk3` content and does not try to install arbitrary extracted scripts or binaries.

Examples:

```bash
alphagsm myqlserver mod add url https://example.invalid/mappack.zip
alphagsm myqlserver mod add url https://example.invalid/pak-custom.pk3
alphagsm myqlserver mod apply
alphagsm myqlserver mod cleanup
```

## Notes

- Module name: `qlserver`
- Default port: 27960

## Developer Notes

### Run File

- **Executable**: `qzeroded.x64`
- **Location**: `<install_dir>/qzeroded.x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `349090`

### Server Configuration

- **Config files**: `baseq3/server.cfg`
- **Template**: See [server-templates/qlserver/](../server-templates/qlserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `hostname` and `startmap` aligned with `set`
- **Current blocker**: anonymous SteamCMD setup alone is not enough; the
  operator must provide the missing Quake Live authentication/config
  prerequisites before `start` can succeed

### Maps and Mods

- **Map directory**: directory containing `servercfg` (default `baseq3/`)
- **Mod directory**: directory containing `servercfg` (default `baseq3/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for Quake Live, install approved `.pk3` payloads into the content directory implied by `servercfg`, and clean up only AlphaGSM-managed files from `.alphagsm/mods/qlserver/`.
- **Workshop support**: No
