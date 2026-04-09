# Legacy CS:GO

This guide covers the legacy `counterstrikeglobaloffensive` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycounters create counterstrikeglobaloffensive
```

Run setup:

```bash
alphagsm mycounters setup
```

Start it:

```bash
alphagsm mycounters start
```

Check it:

```bash
alphagsm mycounters status
```

Stop it:

```bash
alphagsm mycounters stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycounters update
alphagsm mycounters backup
```

## Notes

- Module name: `counterstrikeglobaloffensive`
- Default port: 27015
- Current status: disabled in automated testing. SteamCMD app `740` installs a legacy CS:GO dedicated-server build that now receives `MasterRequestRestart` and shuts itself down while hibernating.
- Valve's current CS2 dedicated-server flow uses app `730` and is exposed separately through [`counterstrike2`](counterstrike2.md).

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `740`

### Server Configuration

- **Config files**: `server.cfg`
- **Template**: See [server-templates/counterstrikeglobaloffensive/](../server-templates/counterstrikeglobaloffensive/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
