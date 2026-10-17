# Call of Duty 4

This guide covers the `cod4server` module in AlphaGSM.

`cod4server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that owned-base-assets
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- owned original-2007 multiplayer assets: `main/iw_*.iwd` and every
  `zone/english/mp_*.ff` map, plus `zone/english/localized_common_mp.ff`
- a legacy disc tree can instead provide `fileSysCheck.cfg` and
  `main/localized_*.iwd`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycod4serv create cod4server
```

For an owned Steam copy, sign in once and let setup acquire the declared files:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm mycod4serv setup --auth-profile owned
```

Enter credentials only at the local SteamCMD prompts. For an existing local
Steam library, use `setup --steam-dir /path/to/SteamLibrary/steamapps` instead.
Authenticated setup of Steam app 7940 imported `main/iw_00.iwd` through
`iw_13.iwd`, `localized_english_iw00.iwd` through `iw06.iwd`, and the
`zone/english` multiplayer fastfiles. It does not need `fileSysCheck.cfg`.
AlphaGSM installs CoD4x `cod4x18_dedrun` for that tree. Local process query
and info answered native Quake getstatus on `mp_crash` and the server
stopped cleanly. Docker was not rerun.

Start it:

```bash
alphagsm mycod4serv start
```

Check it:

```bash
alphagsm mycod4serv status
```

Stop it:

```bash
alphagsm mycod4serv stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads the CoD4x 21.2 `cod4x18_dedrun` binary and marks it executable
- keeps every dedicated multiplayer fastfile and drops campaign fastfiles,
  movies, and client binaries

`cod4server` is supported in `ENABLED (BYO)` mode. AlphaGSM installs the CoD4x
Linux dedicated binary for you. That binary does not include the owned
multiplayer IWDs or fastfiles.

If using setup without an asset source or saved profile, before `start` copy the required owned files from a legitimate Call of Duty 4
installation into the AlphaGSM server tree:

```text
<install_dir>/main/iw_*.iwd
<install_dir>/zone/english/mp_*.ff
<install_dir>/zone/english/localized_common_mp.ff
```

A legacy tree uses these paths instead of the localized fastfile:

```text
<install_dir>/fileSysCheck.cfg
<install_dir>/main/localized_*.iwd
```

Manual-copy alternative:

```bash
alphagsm mycod4serv create cod4server
alphagsm mycod4serv setup
cp /path/to/cod4/fileSysCheck.cfg <install_dir>/
cp /path/to/cod4/main/localized_*.iwd <install_dir>/main/
alphagsm mycod4serv start
```

If the server still exits immediately, a legacy tree needs `fileSysCheck.cfg`
at the server root and `main/localized_*.iwd`. A Steam app 7940 tree instead
needs `zone/english/localized_common_mp.ff`, the shared multiplayer fastfiles,
and every `zone/english/mp_*.ff` map. Do not copy the 2008 archive's
`libstdc++.so.6` or `libgcc_s.so.1` next to `cod4x18_dedrun`.

## Useful Commands

```bash
alphagsm mycod4serv update
alphagsm mycod4serv backup
```

## Notes

- Module name: `cod4server`
- Default port: 28960
- Anonymous setup still needs the owned IWDs and `zone/english/mp_*.ff` maps.
  Local authenticated setup of app 7940 completed a native Quake lifecycle
  on `mp_crash` and stopped cleanly. Docker was not rerun.
- Dedicated installs must contain every multiplayer map. Campaign fastfiles
  such as `ac130.ff` are not required

<!-- alphagsm-server-variables:start -->

## Server variables

After `create cod4server`, inspect or change these with `set`:

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
| `moddir` | — | string | The active Call of Duty 4 mod directory. Example: `baseq3`. |
| `port` | gameport | integer | The game port for the server. Example: `27960`. |
| `startmap` | map, gamemap, level, world | string | The startup map. |
| `url` | — | string | Download URL for the server archive. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `cod4x18_dedrun`
- **Location**: `<install_dir>/cod4x18_dedrun`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- Startup runs `./cod4x18_dedrun` with `+set dedicated 2` and `+set sv_punkbuster 0`, and sets `fs_basepath` and `fs_homepath` to `.` so the server does not use `~/.callofduty4`. It does not set `LD_LIBRARY_PATH=.`. The 2008 archive's `libstdc++.so.6` and `libgcc_s.so.1` are not placed beside CoD4x.
- `sv_authtoken` is only for the CoD4x master list and is not required for a local query.
- CoD4x 21.2 does not publish `main/xbase_00.iwd`. AlphaGSM does not download it. The validated local start ran without that file.
- **Owned base assets still required**: `main/*.iwd`, every `zone/english/mp_*.ff`,
  and either `zone/english/localized_common_mp.ff` or legacy `fileSysCheck.cfg`
  plus `main/localized_*.iwd`
- **Copy targets before first start**: `<install_dir>/main/` for IWDs and
  `<install_dir>/zone/english/` for multiplayer fastfiles
- **Template**: See [server-templates/cod4server/](../server-templates/cod4server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/` (default `<install_dir>/main/`)
- **Workshop support**: No

## Mod Sources

Call of Duty 4 supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir`, tracks only the files it owns, and keeps the active `moddir` in the managed backup targets.

Examples:

```bash
alphagsm mycod4serv mod add url https://example.com/custom.pk3
alphagsm mycod4serv mod add url https://example.com/custom-pack.zip
alphagsm mycod4serv mod apply
alphagsm mycod4serv mod cleanup
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
