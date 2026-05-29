# Stationeers

This guide covers the `stationeersserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- A Linux host/runtime that can start the Unity dedicated server cleanly in headless mode

## Quick Start

Create the server:

```bash
alphagsm mystatione create stationeersserver
```

Run setup:

```bash
alphagsm mystatione setup
```

Start it:

```bash
alphagsm mystatione start
```

Check it:

```bash
alphagsm mystatione status
```

Stop it:

```bash
alphagsm mystatione stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystatione update
alphagsm mystatione backup
```

## Notes

- Module name: `stationeersserver`
- Default game port: `27016/udp`
- Default update port: `27015/udp`
- AlphaGSM query/info contract: generic `udp` on the managed game port

## Developer Notes

### Run File

- **Executable**: `rocketstation_DedicatedServer.x86_64`
- **Location**: `<install_dir>/rocketstation_DedicatedServer.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `600760`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `10`
- **Template**: See [server-templates/stationeersserver/](../server-templates/stationeersserver/) if available
- **Current status**: The Linux direct server path now requires the post-September-2025 launch shape (`-file start ... -logFile ./server.log -settings ... UseSteamP2P false LocalIpAddress 0.0.0.0`). A fresh host probe on 2026-05-29 proved that this path writes `server.log`, loads the `Lunar` world, binds the managed game port as generic `udp`, and answers `udp_ping` while `a2s_info` still times out. The module is still blocked from promotion until the shared disabled-server gate is reopened and the full AlphaGSM lifecycle is rerun on the updated lane.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
