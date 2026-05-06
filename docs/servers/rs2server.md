# Rising Storm 2: Vietnam

This guide covers the `rs2server` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrs2serve create rs2server
```

Run setup:

```bash
alphagsm myrs2serve setup
```

Start it:

```bash
alphagsm myrs2serve start
```

Check it:

```bash
alphagsm myrs2serve status
```

Stop it:

```bash
alphagsm myrs2serve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the A2S query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myrs2serve update
alphagsm myrs2serve backup
```

## Notes

- Module name: `rs2server`
- Default game port: `7777`
- Default query port: `27015`

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/VNGame.exe`
- **Location**: `<install_dir>/Binaries/Win64/VNGame.exe`
- **Engine**: UE3 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `418480`

AlphaGSM launches the server with `-log`, tracks readiness through
`ROGame/Logs/Launch.log`, and waits for `info --json` to report protocol
`a2s` before smoke and integration treat the server as query-ready. The
current smoke and integration checks allow up to 20 minutes for this
Wine/Proton bring-up because RS2 has historically stalled beyond the old
600 second startup window in CI.

### Server Configuration

- **Config file**: `ROGame/Config/PCServer-ROGame.ini`
- `set servername` rewrites `[/Script/Engine.GameReplicationInfo] ServerName` in `ROGame/Config/PCServer-ROGame.ini` through the schema-backed config-sync path.
- **Template**: See [server-templates/rs2server/](../server-templates/rs2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
