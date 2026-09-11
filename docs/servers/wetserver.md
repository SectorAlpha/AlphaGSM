# Wolfenstein: Enemy Territory

This guide covers the `wetserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`
- 32-bit runtime compatibility for the bundled `etded.x86` binary

## Quick Start

Create the server:

```bash
alphagsm mywetserv create wetserver
```

Run setup:

```bash
alphagsm mywetserv setup
```

Start it:

```bash
alphagsm mywetserv start
```

Check it:

```bash
alphagsm mywetserv status
```

Stop it:

```bash
alphagsm mywetserv stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- the official Splash Damage Linux full-game archive URL
- the extracted dedicated server executable path

AlphaGSM downloads the official Linux wrapper zip, extracts the embedded
installer non-interactively, and stages the resulting payload into the server
directory.

## Useful Commands

```bash
alphagsm mywetserv backup
alphagsm mywetserv query
alphagsm mywetserv info
```

## Notes

- Module name: `wetserver`
- LinuxGSM short alias: `wet`
- Default port: 27960
- Query/info protocol: `quake`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create wetserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `configfile` | — | string | Server config file to exec on startup. |
| `dir` | — | string | Install directory for the server. |
| `download_name` | — | string | Cached archive filename. |
| `exe_name` | — | string | Server executable filename. |
| `fs_game` | — | string | The active game/mod directory. Example: `baseq3`. |
| `hostname` | servername, name | string | The advertised server name. Example: `AlphaGSM Arena`. |
| `port` | gameport | integer | The game port for the server. Example: `27960`. |
| `url` | — | string | Download URL for the server archive. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `bin/Linux/x86/etded.x86`
- **Location**: `<install_dir>/bin/Linux/x86/etded.x86`
- **Engine**: id Tech 3 / Quake-family
- **Upstream download**: Splash Damage Linux full-game archive

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `etmain/server.cfg`)
- AlphaGSM rewrites `set net_port` and `set sv_hostname` in the active config file.
- The stock config retains the shipped map rotation such as `exec campaigncycle.cfg`.

### Maps and Mods

- **Game data directory**: `<install_dir>/etmain/`
- **PunkBuster directory**: `<install_dir>/pb/`
- **Workshop support**: No
- **Mod notes**: The initial slice keeps lifecycle support focused on the stock dedicated server payload.