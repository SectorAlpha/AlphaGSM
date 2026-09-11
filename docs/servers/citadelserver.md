# Citadel: Forged With Fire

This guide covers the `citadelserver` module in AlphaGSM.

`citadelserver` remains supported on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `steamcmd-linux` runtime. The current native
Linux payload exposes the validated health surface as TCP on the managed game
port; the configured query port remains published for the game itself but does
not answer A2S reliably in CI. Replacement validation of this corrected
contract is pending.

## Requirements

- Docker
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycitadels create citadelserver
```

Run setup:

```bash
alphagsm mycitadels setup
```

Start it:

```bash
alphagsm mycitadels start
```

Check it:

```bash
alphagsm mycitadels status
```

Stop it:

```bash
alphagsm mycitadels stop
```

## Setup Details

Setup configures:

- the game port (default `7777`)
- the Steam query port (default `27015`)
- the install directory
- SteamCMD downloads the native Linux dedicated-server payload for app `489650`
- AlphaGSM runs the validated Linux path through the shared `steamcmd-linux` Docker runtime

## Useful Commands

```bash
alphagsm mycitadels update
alphagsm mycitadels backup
```

## Notes

- Module name: `citadelserver`
- Default game port: `7777`
- Default query port: `27015`
- Supported Linux health contract: `query`, `info`, and `info --json` use TCP on the managed game port

<!-- alphagsm-server-variables:start -->

## Server variables

After `create citadelserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `map` | gamemap, startmap, level, worldname | string | The startup map. |
| `maxplayers` | users | integer | The maximum number of players. Example: `16`. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |
| `queryport` | — | integer | The query port for the server. Example: `27015`. |
| `servername` | hostname, name | string | The advertised server name. Example: `AlphaGSM Server`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `CitadelServer.sh`
- **Fallback executable**: `Citadel/Binaries/Linux/CitadelServer-Linux-Shipping`
- **Location**: `<install_dir>/CitadelServer.sh`
- **Engine**: Native Linux dedicated server via SteamCMD
- **SteamCMD App ID**: `489650`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `50`
- **Template**: See [server-templates/citadelserver/](../server-templates/citadelserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
