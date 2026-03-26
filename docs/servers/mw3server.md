# Call of Duty: Modern Warfare 3

This guide covers the `mw3server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymw3serve create mw3server
```

Run setup:

```bash
alphagsm mymw3serve setup
```

Start it:

```bash
alphagsm mymw3serve start
```

Check it:

```bash
alphagsm mymw3serve status
```

Stop it:

```bash
alphagsm mymw3serve stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymw3serve update
alphagsm mymw3serve backup
```

## Notes

- Module name: `mw3server`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `iw5mp_server.exe`
- **Location**: `<install_dir>/iw5mp_server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `115310`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `18`
- **Template**: See [server-templates/mw3server/](../server-templates/mw3server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
