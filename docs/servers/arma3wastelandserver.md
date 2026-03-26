# Arma 3 Wasteland

This guide covers the `arma3wastelandserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3was create arma3wastelandserver
```

Run setup:

```bash
alphagsm myarma3was setup
```

Start it:

```bash
alphagsm myarma3was start
```

Check it:

```bash
alphagsm myarma3was status
```

Stop it:

```bash
alphagsm myarma3was stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3was update
alphagsm myarma3was backup
```

## Notes

- Module name: `arma3wastelandserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `arma3server_x64`
- **Location**: `<install_dir>/arma3server_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `233780`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/arma3wastelandserver/](../server-templates/arma3wastelandserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
