# Arma 3 Exile

This guide covers the `arma3exileserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3exi create arma3exileserver
```

Run setup:

```bash
alphagsm myarma3exi setup
```

Start it:

```bash
alphagsm myarma3exi start
```

Check it:

```bash
alphagsm myarma3exi status
```

Stop it:

```bash
alphagsm myarma3exi stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3exi update
alphagsm myarma3exi backup
```

## Notes

- Module name: `arma3exileserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `arma3server_x64`
- **Location**: `<install_dir>/arma3server_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `233780`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/arma3exileserver/](../server-templates/arma3exileserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
