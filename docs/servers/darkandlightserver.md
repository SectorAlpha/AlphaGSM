# Dark and Light

This guide covers the `darkandlightserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydarkandl create darkandlightserver
```

Run setup:

```bash
alphagsm mydarkandl setup
```

Start it:

```bash
alphagsm mydarkandl start
```

Check it:

```bash
alphagsm mydarkandl status
```

Stop it:

```bash
alphagsm mydarkandl stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydarkandl update
alphagsm mydarkandl backup
```

## Notes

- Module name: `darkandlightserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `DNL/Binaries/Win64/DNLServer.exe`
- **Location**: `<install_dir>/DNL/Binaries/Win64/DNLServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `630230`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/darkandlightserver/](../server-templates/darkandlightserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
