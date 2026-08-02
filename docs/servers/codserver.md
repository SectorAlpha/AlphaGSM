# Call of Duty

This guide covers the `codserver` module in AlphaGSM.

`codserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The public dedicated archive supplies the legacy server binary and
base PK3 files but not multiplayer map data, so start requires an owned PK3
containing `maps/mp/<map>.bsp` (or the equivalent map format) staged under the
configured `moddir`. The Docker contract remains available through the shared
`steamcmd-linux` runtime, which supplies the legacy `libstdc++.so.5` library.

## Requirements

- `docker` for the validated anonymous support path
- an owned multiplayer map PK3 staged under `<install_dir>/main/`
- Python packages from `requirements.txt`

Process mode can still work on a host install, but the tested path uses the shared `steamcmd-linux` Docker runtime image because the legacy Call of Duty dedicated binary still expects `libstdc++.so.5`.

## Quick Start

Create the server:

```bash
alphagsm mycodserve create codserver
```

Run setup:

```bash
alphagsm mycodserve setup
```

Start it:

```bash
alphagsm mycodserve start
```

Check it:

```bash
alphagsm mycodserve status
```

Stop it:

```bash
alphagsm mycodserve stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive
- for the validated Docker runtime, the container image remains `ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest`

## Useful Commands

```bash
alphagsm mycodserve update
alphagsm mycodserve backup
```

## Notes

- Module name: `codserver`
- Default port: 28960
- `setup` can download the public server archive, but it does not provide the
  licensed multiplayer maps. AlphaGSM reports an `ENABLED (BYO)` requirement
  before launch when the configured map is not present.

## Developer Notes

### Run File

- **Executable**: `cod_lnxded`
- **Location**: `<install_dir>/cod_lnxded`
- **Engine**: Custom
- **Validated runtime**: Docker via `ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest`

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/codserver/](../server-templates/codserver/) if available
- `query` and `info` currently validate TCP reachability on the configured game port; `info --json` reports protocol `tcp`.

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/`
- **Workshop support**: No

## Mod Sources

Call of Duty supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm mycodserve mod add url https://example.com/mappack.pk3
alphagsm mycodserve mod add url https://example.com/custom-content.zip
alphagsm mycodserve mod apply
alphagsm mycodserve mod cleanup
```
