# Rising World

This guide covers the `rwserver` module in AlphaGSM.

## Requirements

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

- the game port (default 4255)
- the install directory
- SteamCMD downloads the native Linux dedicated server files anonymously

## Useful Commands

```bash
alphagsm myrwserver update
alphagsm myrwserver backup
```

## Notes

- Module name: `rwserver`
- Default game port: `4255`
- Query/info TCP port: `server port - 1` (default `4254`)
- AlphaGSM support status: `PASSED` on the native Linux branch

## Developer Notes

### Run File

- **Executable**: `RisingWorldServer.x64`
- **Location**: `<install_dir>/RisingWorldServer.x64`
- **Engine**: Native Linux
- **SteamCMD App ID**: `339010`

### Server Configuration

- **Config files**: `server.properties`
- **Template**: See [server-templates/rwserver/](../server-templates/rwserver/) if available
- AlphaGSM syncs `Server_Port`, `Server_Name`, and `World_Name`
- The Linux launch path exports `LD_LIBRARY_PATH="<install_dir>/linux64:<install_dir>:$LD_LIBRARY_PATH"` before exec, matching upstream guidance

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `plugins/`
- **Workshop support**: No
