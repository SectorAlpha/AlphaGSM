# Barotrauma

This guide covers the `btserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybtserver create btserver
```

Run setup:

```bash
alphagsm mybtserver setup
```

Start it:

```bash
alphagsm mybtserver start
```

Check it:

```bash
alphagsm mybtserver status
```

Stop it:

```bash
alphagsm mybtserver stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybtserver update
alphagsm mybtserver backup
```

## Notes

- Module name: `btserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `DedicatedServer`
- **Location**: `<install_dir>/DedicatedServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1026340`

### Server Configuration

- **Config files**: `config_player.xml`, `serversettings.xml`
- **Max players**: `16`
- **Template**: See [server-templates/btserver/](../server-templates/btserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
