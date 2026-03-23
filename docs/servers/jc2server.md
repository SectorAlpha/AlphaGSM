# Just Cause 2

This guide covers the `jc2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myjc2serve create jc2server
```

Run setup:

```bash
alphagsm myjc2serve setup
```

Start it:

```bash
alphagsm myjc2serve start
```

Check it:

```bash
alphagsm myjc2serve status
```

Stop it:

```bash
alphagsm myjc2serve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myjc2serve update
alphagsm myjc2serve backup
```

## Notes

- Module name: `jc2server`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `openjc2-server`
- **Location**: `<install_dir>/openjc2-server`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `261140`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `64`
- **Template**: See [server-templates/jc2server/](../server-templates/jc2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
