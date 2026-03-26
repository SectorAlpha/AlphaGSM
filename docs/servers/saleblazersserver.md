# Saleblazers

This guide covers the `saleblazersserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysaleblaz create saleblazersserver
```

Run setup:

```bash
alphagsm mysaleblaz setup
```

Start it:

```bash
alphagsm mysaleblaz start
```

Check it:

```bash
alphagsm mysaleblaz status
```

Stop it:

```bash
alphagsm mysaleblaz stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysaleblaz update
alphagsm mysaleblaz backup
```

## Notes

- Module name: `saleblazersserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `Default/Saleblazers.exe`
- **Location**: `<install_dir>/Default/Saleblazers.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3099600`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/saleblazersserver/](../server-templates/saleblazersserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
