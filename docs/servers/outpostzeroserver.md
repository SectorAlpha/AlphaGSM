# Outpost Zero

This guide covers the `outpostzeroserver` module in AlphaGSM.

Status: PASSED on 2026-05-29

The validated Linux path uses the shared Docker `wine-proton` runtime.

## Requirements

- Docker with the shared Wine/Proton runtime
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myoutpostz create outpostzeroserver
```

Run setup:

```bash
alphagsm myoutpostz setup
```

Start it:

```bash
alphagsm myoutpostz start
```

Check it:

```bash
alphagsm myoutpostz status
```

Stop it:

```bash
alphagsm myoutpostz stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the adjacent game-client/discovery port (default 7778)
- the Steam query port (default 27015)
- the install directory
- SteamCMD downloads the server files
- `WindowsServer/SurvivalGame/Saved/Config/WindowsServer/Game.ini`
- `WindowsServer/SurvivalGame/Binaries/Win64/steam_appid.txt`

## Useful Commands

```bash
alphagsm myoutpostz update
alphagsm myoutpostz backup
```

## Notes

- Module name: `outpostzeroserver`
- Default start map: `RedPlanet`
- Default port: 7777
- Default query port: 27015
- On Linux/Proton, AlphaGSM claims and publishes both documented game-client
  ports. `query`, `info`, and `info --json` use generic `udp` on the adjacent
  discovery port (`port + 1`) after the world reaches `InProgress`.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create outpostzeroserver`, inspect or change these with `set`:

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
| `servername` | hostname, name | string | The advertised server name. Example: `AlphaGSM Server`. |
| `startmap` | map, gamemap, level, world | string | The startup world or map. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `WindowsServer/SurvivalGameServer.exe`
- **Location**: `<install_dir>/WindowsServer/SurvivalGameServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `762880`

### Server Configuration

- **Config file**: `WindowsServer/SurvivalGame/Saved/Config/WindowsServer/Game.ini`
- **Max players**: `16`
- **Template**: See [server-templates/outpostzeroserver/](../server-templates/outpostzeroserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
