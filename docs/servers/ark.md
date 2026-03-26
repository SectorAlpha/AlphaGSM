# ARK: Survival Evolved

This guide covers the `ark` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myark create ark
```

Run setup:

```bash
alphagsm myark setup
```

Start it:

```bash
alphagsm myark start
```

Check it:

```bash
alphagsm myark status
```

Stop it:

```bash
alphagsm myark stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myark update
alphagsm myark backup
```

## Notes

- Module name: `ark`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `ShooterGame/Binaries/Linux/ShooterGameServer`
- **Location**: `<install_dir>/ShooterGame/Binaries/Linux/ShooterGameServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `376030`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/ark/](../server-templates/ark/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
