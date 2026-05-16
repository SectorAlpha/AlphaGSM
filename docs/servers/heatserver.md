# Heat

This guide covers the `heatserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myheatserv create heatserver
```

Run setup:

```bash
alphagsm myheatserv setup
```

Start it:

```bash
alphagsm myheatserv start
```

Check it:

```bash
alphagsm myheatserv status
```

Stop it:

```bash
alphagsm myheatserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the query port (default 27016)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myheatserv update
alphagsm myheatserv backup
```

## Notes

- Module name: `heatserver`
- Default game port: 27015
- Default query port: 27016

## Developer Notes

### Run File

- **Executable**: `HeatServer.exe`
- **Location**: `<install_dir>/Server.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `996600`

AlphaGSM launches the server with `-batchmode -nographics -logFile ./server.log`,
tracks readiness through `server.log`, and waits for `info --json` to report
protocol `a2s` before treating the server as query-ready.

### Server Configuration

- **Config files**: `ServerConfig.cfg`
- **Max players**: `32`
- **Template**: See [server-templates/heatserver/](../server-templates/heatserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
