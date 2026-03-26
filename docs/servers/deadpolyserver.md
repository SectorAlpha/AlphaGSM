# DeadPoly

This guide covers the `deadpolyserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydeadpoly create deadpolyserver
```

Run setup:

```bash
alphagsm mydeadpoly setup
```

Start it:

```bash
alphagsm mydeadpoly start
```

Check it:

```bash
alphagsm mydeadpoly status
```

Stop it:

```bash
alphagsm mydeadpoly stop
```

## Setup Details

Setup configures:

- the game port (default 7779)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydeadpoly update
alphagsm mydeadpoly backup
```

## Notes

- Module name: `deadpolyserver`
- Default port: 7779

## Developer Notes

### Run File

- **Executable**: `DeadPolyServer.sh`
- **Location**: `<install_dir>/DeadPolyServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2208380`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/deadpolyserver/](../server-templates/deadpolyserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
