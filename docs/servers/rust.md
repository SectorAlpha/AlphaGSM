# Rust

This guide covers the `rust` module in AlphaGSM.

`rust` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline.
GitHub integration exercises process and Docker using the same module launch
contract and AlphaGSM-resolved A2S readiness surface.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrust create rust
```

Run setup:

```bash
alphagsm myrust setup
```

Start it:

```bash
alphagsm myrust start
```

Check it:

```bash
alphagsm myrust status
```

Stop it:

```bash
alphagsm myrust stop
```

## Setup Details

Setup configures:

- the game port (default 28015/UDP)
- the RCON port (default 28016/TCP)
- the Steam query port (default 28017/UDP)
- the install directory
- SteamCMD downloads the server files

## Resetting the World

Stop the server, then run `alphagsm myrust reset-world` (or `wipe`). AlphaGSM
lists the world data to delete and asks for confirmation. Add `-Y` to skip the
prompt. Run `start` afterwards to generate a fresh world.

See [world creation and reset](../world-management.md) for exactly which files
are removed and the supported layouts.

## Useful Commands

```bash
alphagsm myrust update
alphagsm myrust backup
```

## Notes

- Module name: `rust`
- Default game port: 28015/UDP
- Default RCON port: 28016/TCP
- Default query port: 28017/UDP
- `query`, `info`, and `info --json` use A2S on `server.queryport`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create rust`, inspect or change these with `set`:

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

- **Executable**: `RustDedicated`
- **Location**: `<install_dir>/RustDedicated`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `258550`
- **Launch ports**: `+server.port`, `+server.queryport`, and
  `+rcon.port`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `50`
- **Template**: See [server-templates/rust/](../server-templates/rust/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
