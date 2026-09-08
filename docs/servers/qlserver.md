# Quake Live

This guide covers the `qlserver` module in AlphaGSM.

`qlserver` retains its existing `ENABLED (BYO)` classification while process and
Docker startup are revalidated in CI. The latest failure was a missing bundled
library search path; it did not establish an authentication requirement.
Local runs use the process runtime unless you select Docker.

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

Anonymous SteamCMD setup installs the dedicated-server payload. AlphaGSM now
adds the bundled `linux64` directory to the launcher's library search path so
`qzeroded.x64` can load `libsteam_api.so`; selecting `qzeroded.x86` uses
`linux32`. This applies to both process and Docker launches. Keep these
library directories beside the executable when staging an installation.

CI validation of this launcher fix is pending. A missing `libsteam_api.so`
error occurs before server authentication and should be diagnosed as a
library-loading problem.

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
- **Current validation**: the bundled Steam API library search path has been
  corrected; process and Docker lifecycle verification is pending CI

### Maps and Mods

- **Map directory**: directory containing `servercfg` (default `baseq3/`)
- **Mod directory**: directory containing `servercfg` (default `baseq3/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for Quake Live, install approved `.pk3` payloads into the content directory implied by `servercfg`, and clean up only AlphaGSM-managed files from `.alphagsm/mods/qlserver/`.
- **Workshop support**: No
