# Palworld

This guide covers the `palworld` module in AlphaGSM.

`palworld` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. GitHub integration keeps process and Docker coverage. The same
create / setup / start / query / stop commands work on both runtimes.

## Requirements

- `screen` (host/process path)
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`) on the host path
- Python packages from `requirements.txt`

The smoke runner waits for Palworld's `Running Palworld dedicated server on :`
message before checking status and stopping the server.

## Quick Start

```bash
alphagsm mypalworld create palworld
alphagsm mypalworld setup
alphagsm mypalworld start
alphagsm mypalworld status
alphagsm mypalworld query
alphagsm mypalworld info
alphagsm mypalworld stop
```

Community (public lobby) mode:

```bash
alphagsm mypalworld setup --community
```

## Setup Details

Setup configures:

- the game port (default 8211)
- the install directory
- SteamCMD downloads the server files
- AlphaGSM copies `DefaultPalWorldSettings.ini` into the Linux dedicated
  settings path on first install
- AlphaGSM passes only Palworld's documented `-port=<port>` network argument;
  there is no separate managed query-port argument

## Useful Commands

```bash
alphagsm mypalworld update
alphagsm mypalworld update -r
alphagsm mypalworld backup
```

`-r` restarts after the SteamCMD update. See
[Updating Servers And AlphaGSM](../updating.md). Palworld has no AlphaGSM
`mod` command.

## Notes

- Module name: `palworld`
- Default port: 8211
- Network protocol: UDP on the game port
- `query`, `info`, and `info --json` use generic UDP health. That proves the
  dedicated port is open; it does not return a rich player/map listing.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create palworld`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `PalServer.sh`
- **Location**: `<install_dir>/PalServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2394010`

### Server Configuration

- **Config files**: `DefaultPalWorldSettings.ini`, `PalWorldSettings.ini`
- **Template**: See [server-templates/palworld/](../server-templates/palworld/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
