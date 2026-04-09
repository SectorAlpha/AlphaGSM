# Unreal Tournament 99

This guide covers the `ut99server` module in AlphaGSM.

## Requirements

- `screen`
- `7z` or `7zz` (`p7zip-full` on Debian/Ubuntu)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myut99serv create ut99server
```

Run setup:

```bash
alphagsm myut99serv setup
```

Start it:

```bash
alphagsm myut99serv start
```

Check it:

```bash
alphagsm myut99serv status
```

Stop it:

```bash
alphagsm myut99serv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and runs the OldUnreal Linux installer
- accepts the Epic Games Terms of Service non-interactively for automated setup

## Useful Commands

```bash
alphagsm myut99serv update
alphagsm myut99serv backup
```

## Notes

- Module name: `ut99server`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: architecture-specific OldUnreal launcher
- **Typical amd64 location**: `<install_dir>/System64/ucc-bin-amd64`
- **Compatibility wrapper**: `<install_dir>/System64/ucc-bin` when present
- **Engine**: Custom

### Server Configuration

- **Config file**: typically `System64/UnrealTournament.ini` on modern Linux installs
- **Max players**: `16`
- **Template**: See [server-templates/ut99server/](../server-templates/ut99server/) if available

### Query and Info

- `alphagsm <server> query` and `alphagsm <server> info` currently use generic UDP reachability
- the screen log at `alphagsm-home/logs/` is the best readiness signal for startup diagnostics

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
