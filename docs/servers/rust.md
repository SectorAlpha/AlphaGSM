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
