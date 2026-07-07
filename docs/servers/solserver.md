# Soldat

This guide covers the `solserver` module in AlphaGSM.

`solserver` is currently `PASSED` in the checked-in support tracker on the
documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane
validates both process and Docker runtimes for this module, while local runs
remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysolserve create solserver
```

Run setup:

```bash
alphagsm mysolserve setup
```

Start it:

```bash
alphagsm mysolserve start
```

Check it:

```bash
alphagsm mysolserve status
```

Stop it:

```bash
alphagsm mysolserve stop
```

## Setup Details

Setup configures:

- the game port (default 23073)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysolserve update
alphagsm mysolserve backup
```

## Notes

- Module name: `solserver`
- Default port: 23073

## Developer Notes

### Run File

- **Executable**: `soldatserver`
- **Location**: `<install_dir>/soldatserver`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `638500`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `16`
- **Template**: See [server-templates/solserver/](../server-templates/solserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
