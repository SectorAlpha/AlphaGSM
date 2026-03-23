# Squad 44

This guide covers the `squad44server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysquad44s create squad44server
```

Run setup:

```bash
alphagsm mysquad44s setup
```

Start it:

```bash
alphagsm mysquad44s start
```

Check it:

```bash
alphagsm mysquad44s status
```

Stop it:

```bash
alphagsm mysquad44s stop
```

## Setup Details

Setup configures:

- the game port (default 27165)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysquad44s update
alphagsm mysquad44s backup
```

## Notes

- Module name: `squad44server`
- Default port: 27165

## Developer Notes

### Run File

- **Executable**: `PostScriptumServer.sh`
- **Location**: `<install_dir>/PostScriptumServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `746200`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/squad44server/](../server-templates/squad44server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
