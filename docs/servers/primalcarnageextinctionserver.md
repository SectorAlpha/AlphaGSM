# Primal Carnage: Extinction

This guide covers the `primalcarnageextinctionserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprimalca create primalcarnageextinctionserver
```

Run setup:

```bash
alphagsm myprimalca setup
```

Start it:

```bash
alphagsm myprimalca start
```

Check it:

```bash
alphagsm myprimalca status
```

Stop it:

```bash
alphagsm myprimalca stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the A2S query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myprimalca update
alphagsm myprimalca backup
```

## Notes

- Module name: `primalcarnageextinctionserver`
- Default game port: `7777`
- Default query port: `27015`

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/PrimalCarnageServer.exe`
- **Location**: `<install_dir>/Binaries/Win64/PrimalCarnageServer.exe`
- **Engine**: UE3 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `336400`

AlphaGSM launches the dedicated server with `server -log`, tracks readiness
through `PrimalCarnageGame/Logs/Launch.log`, and queries A2S on the dedicated
`queryport` via the resolved local query host before treating the server as
query-ready.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/primalcarnageextinctionserver/](../server-templates/primalcarnageextinctionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
