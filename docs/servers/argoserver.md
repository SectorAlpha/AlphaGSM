# Argo

This guide covers the `argoserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myargoserv create argoserver
```

Run setup:

```bash
alphagsm myargoserv setup
```

Start it:

```bash
alphagsm myargoserv start
```

Check it:

```bash
alphagsm myargoserv status
```

Stop it:

```bash
alphagsm myargoserv stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myargoserv update
alphagsm myargoserv backup
```

## Notes

- Module name: `argoserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `argo_server_x64`
- **Location**: `<install_dir>/argo_server_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `563930`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/argoserver/](../server-templates/argoserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
