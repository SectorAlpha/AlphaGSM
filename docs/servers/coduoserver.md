# Call of Duty: United Offensive

This guide covers the `coduoserver` module in AlphaGSM.

`coduoserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that owned-base-assets
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- owned base Call of Duty multiplayer assets that include `main/pak0.pk3` or
  `main/default_mp.cfg`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycoduoser create coduoserver
```

For an owned Steam copy, sign in once and let setup acquire the declared files:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm mycoduoser setup --auth-profile owned
```

Enter credentials only at the local SteamCMD prompts. For an existing local
Steam library, use `setup --steam-dir /path/to/SteamLibrary/steamapps` instead.
Local process setup with an entitled profile was validated on 2026-10-16.
Query and info use Quake UDP getstatus on the game port. Docker was not rerun.

Start it:

```bash
alphagsm mycoduoser start
```

Check it:

```bash
alphagsm mycoduoser status
```

Stop it:

```bash
alphagsm mycoduoser stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive
- still requires copied base Call of Duty multiplayer assets before the server
  can finish startup

`coduoserver` is supported in `ENABLED (BYO)` mode. AlphaGSM installs the dedicated
binary for Call of Duty: United Offensive, but the archive still depends on
owned base Call of Duty multiplayer files that are not bundled.

If using setup without an asset source or saved profile, before `start` copy the required files from a legitimate base Call of Duty
installation into the AlphaGSM server tree:

```text
<install_dir>/main/pak0.pk3
<install_dir>/main/default_mp.cfg
```

A manual tree also needs the expansion PK3s under `uo/`, including the
multiplayer map `maps/mp/mp_uo_stanjel.bsp`. The default start map
`mp_brecourt` is stored in the base `main` PK3s. Authenticated setup downloads
base app 2620 and expansion app 2640, keeps the English multiplayer PK3s, and
drops client executables and non-English localization PK3s.

Manual-copy alternative:

```bash
alphagsm mycoduoser create coduoserver
alphagsm mycoduoser setup
cp /path/to/cod/main/pak0.pk3 <install_dir>/main/
cp /path/to/cod/main/default_mp.cfg <install_dir>/main/
alphagsm mycoduoser start
```

## Useful Commands

```bash
alphagsm mycoduoser update
alphagsm mycoduoser backup
```

## Notes

- Module name: `coduoserver`
- Default port: 28960
- Current blocker for anonymous installs: the dedicated archive still depends
  on owned base Call of Duty assets such as `main/pak0.pk3` or
  `main/default_mp.cfg`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create coduoserver`, inspect or change these with `set`:

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
| `moddir` | — | string | The active Call of Duty: United Offensive mod directory. Example: `baseq3`. |
| `port` | gameport | integer | The game port for the server. Example: `27960`. |
| `startmap` | map, gamemap, level, world | string | The startup map. |
| `url` | — | string | Download URL for the server archive. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `coduoded_lnxded`
- **Location**: `<install_dir>/coduoded_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `uo/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- Setup stages the upstream gcc 3.2 libraries beside `coduo_lnxded` and starts it with `LD_LIBRARY_PATH=.`, `fs_basepath` `.`, and `fs_homepath` `.` so the dedicated server does not use `~/.callofduty`.
- **Owned base assets still required**: `main/pak0.pk3`,
  `main/default_mp.cfg`
- **Copy target before first start**: `<install_dir>/main/`
- **Template**: See [server-templates/coduoserver/](../server-templates/coduoserver/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/`
- **Workshop support**: No

## Mod Sources

Call of Duty: United Offensive supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm mycoduoser mod add url https://example.com/mappack.pk3
alphagsm mycoduoser mod add url https://example.com/custom-content.zip
alphagsm mycoduoser mod apply
alphagsm mycoduoser mod cleanup
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
See [BYO files and private SteamCMD acquisition](../byo-files.md).
