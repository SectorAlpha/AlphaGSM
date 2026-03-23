# Rising World

This guide covers the `rwserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrwserver create rwserver
```

Run setup:

```bash
alphagsm myrwserver setup
```

Start it:

```bash
alphagsm myrwserver start
```

Check it:

```bash
alphagsm myrwserver status
```

Stop it:

```bash
alphagsm myrwserver stop
```

## Setup Details

Setup configures:

- the game port (default 4254)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myrwserver update
alphagsm myrwserver backup
```

## Notes

- Module name: `rwserver`
- Default port: 4254

## Developer Notes

### Run File

- **Executable**: `server.jar`
- **Location**: `<install_dir>/server.jar`
- **Engine**: Java / Custom
- **SteamCMD App ID**: `339010`

### Server Configuration

- **Config files**: `server.properties`
- **Template**: See [server-templates/rwserver/](../server-templates/rwserver/) if available

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `plugins/`
- **Workshop support**: No
