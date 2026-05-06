# Remnants

This guide covers the `remnantsserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myremnants create remnantsserver
```

Run setup:

```bash
alphagsm myremnants setup
```

Start it:

```bash
alphagsm myremnants start
```

Check it:

```bash
alphagsm myremnants status
```

Stop it:

```bash
alphagsm myremnants stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myremnants update
alphagsm myremnants backup
```

## Notes

- Module name: `remnantsserver`
- Default game port: 7777
- Default query port: 27015

## Developer Notes

### Run File

- **Executable**: `RemSurvivalServer.exe`
- **Location**: `<install_dir>/RemSurvivalServer.exe`
- **Engine**: UE4 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `1141420`

Smoke and integration validation track readiness through
`RemSurvival/Saved/Logs/RemSurvival.log` and then confirm `info --json`
reports protocol `a2s`.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/remnantsserver/](../server-templates/remnantsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
