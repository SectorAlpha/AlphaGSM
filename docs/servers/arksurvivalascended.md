# ARK: Survival Ascended

This guide covers the `arksurvivalascended` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarksurvi create arksurvivalascended
```

Run setup:

```bash
alphagsm myarksurvi setup
```

Start it:

```bash
alphagsm myarksurvi start
```

Check it:

```bash
alphagsm myarksurvi status
```

Stop it:

```bash
alphagsm myarksurvi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarksurvi update
alphagsm myarksurvi backup
```

## Notes

- Module name: `arksurvivalascended`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `ShooterGame/Binaries/Win64/ArkAscendedServer.exe`
- **Location**: `<install_dir>/ShooterGame/Binaries/Win64/ArkAscendedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2430930`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/arksurvivalascended/](../server-templates/arksurvivalascended/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
