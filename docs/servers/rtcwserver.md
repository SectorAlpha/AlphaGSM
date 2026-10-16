# Return to Castle Wolfenstein

This guide covers the `rtcwserver` module in AlphaGSM.

`rtcwserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that owned-base-assets
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- Python packages from `requirements.txt`
- Original Return to Castle Wolfenstein multiplayer assets in `main/`
  - `mp_bin.pk3`
  - `mp_pak0.pk3` through `mp_pak5.pk3`
  - `mp_pakmaps0.pk3` through `mp_pakmaps6.pk3`

## Quick Start

Create the server:

```bash
alphagsm myrtcwserv create rtcwserver
```

For an owned Steam copy, sign in once and let setup acquire the declared files:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm myrtcwserv setup --auth-profile owned
```

Enter credentials only at the local SteamCMD prompts. For an existing local
Steam library, use `setup --steam-dir /path/to/SteamLibrary/steamapps` instead.
The authenticated download path still needs local validation.

Start it:

```bash
alphagsm myrtcwserv start
```

Check it:

```bash
alphagsm myrtcwserv status
```

Stop it:

```bash
alphagsm myrtcwserv stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

This server is supported in `ENABLED (BYO)` mode. When using setup without an
asset source or saved profile, copy the original RTCW multiplayer PK3 set into the install's
`main/` directory. The public ioRTCW engine release is not enough by itself for
the dedicated multiplayer server.

## Useful Commands

```bash
alphagsm myrtcwserv update
alphagsm myrtcwserv backup
```

## Mod Sources

RTCW content management currently targets the active `fs_game` directory under
the server root. By default that is `main/`, but if you set a custom `fs_game`
value, AlphaGSM installs into that directory instead.

- Current mod source support is direct `url` entries only.
- `mod add url <https-url>` accepts direct `.pk3` URLs and supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload exposes either `<fs_game>/<name>.pk3` or bare `.pk3` files at the archive root.
- `mod cleanup` removes only AlphaGSM-tracked `.pk3` files and keeps its cache/state under `.alphagsm/mods/rtcwserver/`.
- The first RTCW slice intentionally stops at `.pk3` content and does not try to install arbitrary extracted scripts or binaries.

Examples:

```bash
alphagsm myrtcwserv mod add url https://example.invalid/mappack.zip
alphagsm myrtcwserv mod add url https://example.invalid/pak-custom.pk3
alphagsm myrtcwserv mod apply
alphagsm myrtcwserv mod cleanup
```

## Notes

- Module name: `rtcwserver`
- Default port: 27960

<!-- alphagsm-server-variables:start -->

## Server variables

After `create rtcwserver`, inspect or change these with `set`:

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
| `fs_game` | — | string | The active game/mod directory. |
| `hostname` | servername, name | string | The advertised server name. |
| `port` | gameport | integer | The game port for the server. Example: `27960`. |
| `startmap` | map, gamemap, level, world | string | The startup map. |
| `url` | — | string | Download URL for the server archive. |
| `version` | — | string | Requested upstream release version. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `iowolfded.x86_64`
- **Location**: `<install_dir>/iowolfded.x86_64`
- **Engine**: Custom
- **Owned assets required before start**: `main/mp_bin.pk3`, `main/mp_pak0.pk3` through `main/mp_pak5.pk3`, and `main/mp_pakmaps0.pk3` through `main/mp_pakmaps6.pk3`

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set fs_game`, and `set map` rewrite `<fs_game>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/rtcwserver/](../server-templates/rtcwserver/) if available

### Maps and Mods

- **Map directory**: `<fs_game>/` (default `main/`)
- **Mod directory**: `<fs_game>/` (default `main/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for RTCW, install approved `.pk3` payloads into the active `fs_game` directory, and clean up only AlphaGSM-managed files from `.alphagsm/mods/rtcwserver/`.
- **Workshop support**: No

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
See [BYO files and private SteamCMD acquisition](../byo-files.md).
