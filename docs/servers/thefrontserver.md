# The Front

This guide covers the `thefrontserver` module in AlphaGSM.

`thefrontserver` retains its historical `PASSED` status on the documented
Ubuntu 24.04 Linux baseline. The current non-root Docker correction is pending
replacement GitHub CI across the process and Docker lifecycle lanes and does
not record a new pass. The game command remains aligned across both backends,
while local runs stay process-backed by default unless you opt into Docker.

## Requirements

- a non-root AlphaGSM user
- `screen` for the process runtime
- Docker for the Docker runtime
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mythefront create thefrontserver
```

Run setup:

```bash
alphagsm mythefront setup
```

Start it:

```bash
alphagsm mythefront start
```

Check it:

```bash
alphagsm mythefront status
```

Stop it:

```bash
alphagsm mythefront stop
```

## Setup Details

Setup configures:

- the game port (default `7777`)
- the Steam query port (defaults to `port + 2` unless you already set `queryport`)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mythefront update
alphagsm mythefront backup
```

## Notes

- Module name: `thefrontserver`
- Default game port: `7777`
- Default beacon port: `7778`
- Default query port: `7779`
- Default shutdown-service port: `7780`
- The Docker runtime launches the server as AlphaGSM's effective host UID/GID.
  Running AlphaGSM itself as root is rejected for this module's Docker path.
- When using `alphagsm-docker`, the wrapper derives that identity from the
  invoking process, propagates the Docker socket group, and recreates an old
  root or stale-group manager before The Front starts.
- Docker HOME state is kept under AlphaGSM's manager-owned
  `runtime/<server>/home` directory, outside the writable game installation.
  `alphagsm mythefront doctor` reports identity, HOME-mount, ownership, mode,
  and first-run creatability problems before launch.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create thefrontserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `maxplayers` | users | integer | The maximum number of players. Example: `16`. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |
| `queryport` | — | integer | The query port for the server. Example: `27015`. |
| `servername` | hostname, name | string | The advertised server name. |
| `worldname` | world, map, gamemap, levelname | string | The world name. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `ProjectWar/Binaries/Linux/TheFrontServer`
- **Location**: `<install_dir>/ProjectWar/Binaries/Linux/TheFrontServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2334200`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Launch shape**: `TheFrontServer ProjectWar ProjectWar_Start?Listen?MaxPlayers=<n> -server -game ... -port=<port> -BeaconPort=<port+1> -QueryPort=<port+2> -ShutDownServicePort=<port+3>`
- **Template**: See [server-templates/thefrontserver/](../server-templates/thefrontserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
