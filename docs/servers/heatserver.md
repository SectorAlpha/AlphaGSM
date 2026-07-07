# Heat

This guide covers the `heatserver` module in AlphaGSM.

`heatserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

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

- the game port (stored in `Configuration/ServerSettings.cfg` as `portNumber`)
- the query port (stored in `Configuration/ServerSettings.cfg` as `steamAuthPort`)
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

- **Executable**: `Server.exe`
- **Location**: `<install_dir>/Server.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `996600`

AlphaGSM starts the upstream `Server.exe` console directly and the real server
readiness signal lives under `Logs/Console*.txt` / `Logs/Dedi*.txt`, not a root
`server.log`.

Current `release_v1` behavior: AlphaGSM bootstraps a missing
`Configuration/ServerSettings.cfg` by running the upstream first-launch config
generation pass before the real managed start, then rewrites `portNumber`,
`steamAuthPort`, `maxPlayers`, and `levelName` from the datastore.

Validation status: enabled on 2026-05-29. A fresh SteamCMD-managed lifecycle
now passes end to end on `release_v1`, including first-start config bootstrap,
readiness from `Logs/Console*.txt`, A2S `query`, `info`, `info --json`, and
clean shutdown on the managed `queryport`.

### Server Configuration

- **Config files**: `Configuration/ServerSettings.cfg`
- **Max players**: `32`
- **Template**: See [server-templates/heatserver/](../server-templates/heatserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
