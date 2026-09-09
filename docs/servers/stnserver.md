# Survive the Nights

This guide covers the `stnserver` module in AlphaGSM.

`stnserver` is currently `PASSED` in the checked-in support tracker on the
documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane
validates both process and Docker runtimes for this module, while local runs
remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystnserve create stnserver
```

Run setup:

```bash
alphagsm mystnserve setup
```

Start it:

```bash
alphagsm mystnserve start
```

Check it:

```bash
alphagsm mystnserve status
```

Stop it:

```bash
alphagsm mystnserve stop
```

## Setup Details

Setup configures:

- the game port (default 8888)
- a separate Steam query port (game port + 1 unless explicitly set)
- the install directory
- SteamCMD downloads the server files
- AlphaGSM copies missing files from the server's shipped `Config_Template`
  tree into `Config` and preserves files already edited by the operator

## Useful Commands

```bash
alphagsm mystnserve update
alphagsm mystnserve backup
alphagsm mystnserve set port 9999
```

`set port` and `set queryport` rewrite `Config/ServerConfig.txt` immediately through the schema-backed config-sync path. The shared alias layer also accepts `gameport` for this module.

## Notes

- Module name: `stnserver`
- Default port: 8888

## Developer Notes

### Run File

- **Executable**: `Server_Linux_x64`
- **Location**: `<install_dir>/Server_Linux_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1502300`

### Server Configuration

- **Config file**: `Config/ServerConfig.txt`
- **Template**: See [server-templates/stnserver/](../server-templates/stnserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `ServerPort=` aligned with `set port` and `QueryPort=` aligned with `set queryport`
- **First setup**: required files such as `TpPresets.json`, user permissions,
  and StreamLabs defaults are seeded from the installed server payload

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
