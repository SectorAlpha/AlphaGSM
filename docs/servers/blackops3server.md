# Call of Duty: Black Ops III

This guide covers the `blackops3server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myblackops create blackops3server
```

Run setup:

```bash
alphagsm myblackops setup
```

Start it:

```bash
alphagsm myblackops start
```

Check it:

```bash
alphagsm myblackops status
```

Stop it:

```bash
alphagsm myblackops stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myblackops update
alphagsm myblackops backup
```

## Notes

- Module name: `blackops3server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `BlackOps3Server.exe`
- **Location**: `<install_dir>/BlackOps3Server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `545990`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `18`
- **Template**: See [server-templates/blackops3server/](../server-templates/blackops3server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
