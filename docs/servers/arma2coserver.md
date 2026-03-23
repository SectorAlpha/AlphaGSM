# Arma 2 Combined Operations

This guide covers the `arma2coserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma2cos create arma2coserver
```

Run setup:

```bash
alphagsm myarma2cos setup
```

Start it:

```bash
alphagsm myarma2cos start
```

Check it:

```bash
alphagsm myarma2cos status
```

Stop it:

```bash
alphagsm myarma2cos stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma2cos update
alphagsm myarma2cos backup
```

## Notes

- Module name: `arma2coserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `arma2oaserver`
- **Location**: `<install_dir>/arma2oaserver`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `33935`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/arma2coserver/](../server-templates/arma2coserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
