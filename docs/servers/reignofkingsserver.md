# Reign Of Kings

This guide covers the `reignofkingsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myreignofk create reignofkingsserver
```

Run setup:

```bash
alphagsm myreignofk setup
```

Start it:

```bash
alphagsm myreignofk start
```

Check it:

```bash
alphagsm myreignofk status
```

Stop it:

```bash
alphagsm myreignofk stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myreignofk update
alphagsm myreignofk backup
```

## Notes

- Module name: `reignofkingsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Server.exe`
- **Location**: `<install_dir>/Server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `381690`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `40`
- **Template**: See [server-templates/reignofkingsserver/](../server-templates/reignofkingsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
