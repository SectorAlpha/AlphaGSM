# Conan Exiles

This guide covers the `conanexiles` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myconanexi create conanexiles
```

Run setup:

```bash
alphagsm myconanexi setup
```

Start it:

```bash
alphagsm myconanexi start
```

Check it:

```bash
alphagsm myconanexi status
```

Stop it:

```bash
alphagsm myconanexi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myconanexi update
alphagsm myconanexi backup
```

## Notes

- Module name: `conanexiles`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `ConanSandbox/Binaries/Linux/ConanSandboxServer`
- **Location**: `<install_dir>/ConanSandbox/Binaries/Linux/ConanSandboxServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `443030`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `40`
- **Template**: See [server-templates/conanexiles/](../server-templates/conanexiles/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
