# Arma 3 Altis Life

This guide covers the `arma3altislifeserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3alt create arma3altislifeserver
```

Run setup:

```bash
alphagsm myarma3alt setup
```

Start it:

```bash
alphagsm myarma3alt start
```

Check it:

```bash
alphagsm myarma3alt status
```

Stop it:

```bash
alphagsm myarma3alt stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3alt update
alphagsm myarma3alt backup
```

## Notes

- Module name: `arma3altislifeserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `arma3server_x64`
- **Location**: `<install_dir>/arma3server_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `233780`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/arma3altislifeserver/](../server-templates/arma3altislifeserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
