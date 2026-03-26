# Mount & Blade II: Bannerlord

This guide covers the `bannerlordserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybannerlo create bannerlordserver
```

Run setup:

```bash
alphagsm mybannerlo setup
```

Start it:

```bash
alphagsm mybannerlo start
```

Check it:

```bash
alphagsm mybannerlo status
```

Stop it:

```bash
alphagsm mybannerlo stop
```

## Setup Details

Setup configures:

- the game port (default 7210)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybannerlo update
alphagsm mybannerlo backup
```

## Notes

- Module name: `bannerlordserver`
- Default port: 7210

## Developer Notes

### Run File

- **Executable**: `Bannerlord.DedicatedServer`
- **Location**: `<install_dir>/Bannerlord.DedicatedServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1863440`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/bannerlordserver/](../server-templates/bannerlordserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
