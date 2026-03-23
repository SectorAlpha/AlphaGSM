# Primal Carnage: Extinction

This guide covers the `primalcarnageextinctionserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprimalca create primalcarnageextinctionserver
```

Run setup:

```bash
alphagsm myprimalca setup
```

Start it:

```bash
alphagsm myprimalca start
```

Check it:

```bash
alphagsm myprimalca status
```

Stop it:

```bash
alphagsm myprimalca stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myprimalca update
alphagsm myprimalca backup
```

## Notes

- Module name: `primalcarnageextinctionserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `PCEdedicated.exe`
- **Location**: `<install_dir>/PCEdedicated.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `336400`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/primalcarnageextinctionserver/](../server-templates/primalcarnageextinctionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
