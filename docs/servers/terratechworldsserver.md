# TerraTech Worlds

This guide covers the `terratechworldsserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myterratec create terratechworldsserver
```

Run setup:

```bash
alphagsm myterratec setup
```

Start it:

```bash
alphagsm myterratec start
```

Check it:

```bash
alphagsm myterratec status
```

Stop it:

```bash
alphagsm myterratec stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myterratec update
alphagsm myterratec backup
```

## Notes

- Module name: `terratechworldsserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `TT2Server.exe`
- **Location**: `<install_dir>/TT2Server.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2533070`

AlphaGSM launches the server with `-log`, and readiness is tracked through
`Saved/Logs/TT2.log` instead of the screen log.

### Server Configuration

- **Config files**: `dedicated_server_config.json`
- **Template**: See [server-templates/terratechworldsserver/](../server-templates/terratechworldsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
