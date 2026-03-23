# Arma 3 Epoch

This guide covers the `arma3epochserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3epo create arma3epochserver
```

Run setup:

```bash
alphagsm myarma3epo setup
```

Start it:

```bash
alphagsm myarma3epo start
```

Check it:

```bash
alphagsm myarma3epo status
```

Stop it:

```bash
alphagsm myarma3epo stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3epo update
alphagsm myarma3epo backup
```

## Notes

- Module name: `arma3epochserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `arma3server_x64`
- **Location**: `<install_dir>/arma3server_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `233780`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/arma3epochserver/](../server-templates/arma3epochserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
