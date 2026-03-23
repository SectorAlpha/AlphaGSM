# Hell Let Loose

This guide covers the `hellletlooseserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhellletl create hellletlooseserver
```

Run setup:

```bash
alphagsm myhellletl setup
```

Start it:

```bash
alphagsm myhellletl start
```

Check it:

```bash
alphagsm myhellletl status
```

Stop it:

```bash
alphagsm myhellletl stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myhellletl update
alphagsm myhellletl backup
```

## Notes

- Module name: `hellletlooseserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `HLLServer.exe`
- **Location**: `<install_dir>/HLLServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `822500`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/hellletlooseserver/](../server-templates/hellletlooseserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
