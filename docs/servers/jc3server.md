# Just Cause 3

This guide covers the `jc3server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myjc3serve create jc3server
```

Run setup:

```bash
alphagsm myjc3serve setup
```

Start it:

```bash
alphagsm myjc3serve start
```

Check it:

```bash
alphagsm myjc3serve status
```

Stop it:

```bash
alphagsm myjc3serve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myjc3serve update
alphagsm myjc3serve backup
```

## Notes

- Module name: `jc3server`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `openjc3-server`
- **Location**: `<install_dir>/openjc3-server`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `619960`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `64`
- **Template**: See [server-templates/jc3server/](../server-templates/jc3server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
