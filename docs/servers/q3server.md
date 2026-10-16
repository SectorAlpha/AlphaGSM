# Quake 3 Arena

This guide covers the `q3server` module in AlphaGSM.

`q3server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that owned-base-assets prerequisite, while
local runs remain process-backed by default unless you opt into the Docker
backend.

## Requirements

- `screen`
- Python packages from `requirements.txt`
- legitimate Quake III Arena data, acquired from an owned Steam copy or imported locally

The public ioquake3 Linux engine build does not bundle licensed Quake III
base game data. Authenticated setup acquires the declared owned files separately.
Without `baseq3/pak0.pk3`, the dedicated server exits immediately before it can
reach a playable or queryable state.

## Quick Start

Create the server:

```bash
alphagsm myq3server create q3server
```

For an owned Steam copy, sign in once and let setup acquire the declared files:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm myq3server setup --auth-profile owned
```

Enter credentials only at the local SteamCMD prompts. For an existing local
Steam library, use `setup --steam-dir /path/to/SteamLibrary/steamapps` instead.
Authenticated setup and the native process lifecycle were validated locally on
2026-10-16; Docker was not rerun in that local test.

Start it:

```bash
alphagsm myq3server start
```

Check it:

```bash
alphagsm myq3server status
```

Stop it:

```bash
alphagsm myq3server stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads the ioquake3 Linux engine archive and installs its dedicated engine/server game code
- keeps all nine base/patch PK3 packs intact, including their 36 maps and supporting content
- omits the known loose client executable, renderers and client-only engine modules

This server is supported in `ENABLED (BYO)` mode. When using setup without an
asset source or saved profile, copy your legitimate Quake III `pak0.pk3` into
`<install_dir>/baseq3/` before running `start`. Upstream also recommends adding
the freely available Quake III 1.32 point-release patch data (`pak1.pk3`
through `pak8.pk3`) alongside it.

## Useful Commands

```bash
alphagsm myq3server update
alphagsm myq3server backup
```

## Mod Sources

Quake 3 content management currently targets the active `fs_game` directory
under the server root. By default that is `baseq3/`, but if you set a custom
`fs_game` value, AlphaGSM installs into that directory instead.

- Current mod source support is direct `url` entries only.
- `mod add url <https-url>` accepts direct `.pk3` URLs and supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload exposes either `<fs_game>/<name>.pk3` or bare `.pk3` files at the archive root.
- `mod cleanup` removes only AlphaGSM-tracked `.pk3` files and keeps its cache/state under `.alphagsm/mods/q3server/`.
- The first Q3 slice intentionally stops at `.pk3` content and does not try to install arbitrary extracted scripts or binaries.

Examples:

```bash
alphagsm myq3server mod add url https://example.invalid/mappack.zip
alphagsm myq3server mod add url https://example.invalid/pak-custom.pk3
alphagsm myq3server mod apply
alphagsm myq3server mod cleanup
```

## Notes

- Module name: `q3server`
- Default port: 27960

<!-- alphagsm-server-variables:start -->

## Server variables

After `create q3server`, inspect or change these with `set`:

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

- **Executable**: `ioq3ded.x86_64`
- **Location**: `<install_dir>/ioq3ded.x86_64`
- **Engine**: ioquake3 Linux build

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `baseq3/server.cfg`)
- `set servername`, `set fs_game`, and `set map` rewrite `<fs_game>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/q3server/](../server-templates/q3server/) if available

### Maps and Mods

- **Map directory**: `<fs_game>/` (default `baseq3/`)
- **Mod directory**: `<fs_game>/` (default `baseq3/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for Quake 3, install approved `.pk3` payloads into the active `fs_game` directory, and clean up only AlphaGSM-managed files from `.alphagsm/mods/q3server/`.
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
Local validation on 2026-10-16 acquired `pak0.pk3` through `pak8.pk3`, passed
file checks and doctor, reused the remembered profile without another Steam
download, and verified native Quake UDP query/info on `q3dm17`. The test ended
stopped with no owned process or bound UDP port; Docker was not rerun.
See [BYO files and private SteamCMD acquisition](../byo-files.md).

The dedicated-only engine install was also rechecked with the same native
lifecycle. All nine PK3 hashes and 36 maps remained intact; 11 known loose
client-only engine components were omitted.
