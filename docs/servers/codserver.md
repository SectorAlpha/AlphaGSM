# Call of Duty

This guide covers the `codserver` module in AlphaGSM.

`codserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The public dedicated archive supplies the legacy server binary and
base PK3 files but not multiplayer map data, so start requires an owned PK3
containing `maps/mp/<map>.bsp` (or the equivalent map format) staged under the
configured `moddir`. A local process run on 2026-10-16 answered Quake UDP
`getstatus` after setup staged the upstream gcc 3.2 libraries beside
`cod_lnxded`. The Docker contract remains available through the shared
`steamcmd-linux` runtime and was not rerun in that local campaign.

## Requirements

- `docker` for the validated anonymous support path
- an owned multiplayer map PK3 staged under `<install_dir>/main/`
- Python packages from `requirements.txt`

Process mode stages `libstdc++.so.5` and `libgcc_s.so.1` beside `cod_lnxded` and was locally validated. The shared `steamcmd-linux` image also provides `libstdc++.so.5` for container runs.

## Quick Start

Create the server:

```bash
alphagsm mycodserve create codserver
```

For an owned Steam copy, sign in once and let setup acquire the declared files:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm mycodserve setup --auth-profile owned
```

Enter credentials only at the local SteamCMD prompts. For an existing local
Steam library, use `setup --steam-dir /path/to/SteamLibrary/steamapps` instead.
The authenticated download path still needs local validation.

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

<!-- alphagsm-server-variables:start -->

## Server variables

After `create codserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `download_name` | — | string | Cached archive filename. |
| `exe_name` | — | string | Server executable filename. |
| `hostname` | servername, name | string | The advertised server name. |
| `moddir` | — | string | The active Call of Duty mod directory. Example: `baseq3`. |
| `port` | gameport | integer | The game port for the server. Example: `27960`. |
| `startmap` | map, gamemap, level, world | string | The startup map. |
| `url` | — | string | Download URL for the server archive. |

<!-- alphagsm-server-variables:end -->

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
- `query` and `info` use Quake UDP `getstatus` on the game port. `info --json` reports protocol `quake`.
- Setup stages the upstream gcc 3.2 libraries `libstdc++.so.5` and `libgcc_s.so.1` beside `cod_lnxded` and starts it with `LD_LIBRARY_PATH=.`.
- Startup sets `fs_basepath` and `fs_homepath` to the install directory so the dedicated server does not use `~/.callofduty`.

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

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
The preferred Steam-owned path is `alphagsm steam-auth login owned <username>`,
then `alphagsm <server-name> setup --auth-profile owned`. Setup remembers the
profile name and fetches missing required files before installing the engine.
Use `setup --steam-dir /path/to/SteamLibrary/steamapps` to import from an existing
Steam library instead. Direct file acquisition remains available through
`assets fetch steam-owned --auth-profile owned`.
Authenticated downloads remain unverified here.
The base-file helper checks PK3 archives for the configured multiplayer map in
`.bsp` or `.d3dbsp` format. Archive member names may vary in case or use either
slash style; installed filesystem paths must match the native server layout.
See [BYO files and private SteamCMD acquisition](../byo-files.md).
