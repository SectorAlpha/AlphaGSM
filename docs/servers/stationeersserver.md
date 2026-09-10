# Stationeers

This guide covers the `stationeersserver` module in AlphaGSM.

`stationeersserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection, and the validated SteamCMD-backed Linux
lifecycle stays aligned across both backends while local runs remain
process-backed by default unless you opt into the Docker backend.

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

<!-- alphagsm-server-variables:start -->

## Server variables

After `create stationeersserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `serverpassword` | sv_password, password | string | Password required to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

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
- **Current status**: A fresh smoke rerun and focused SteamCMD integration on 2026-05-29 now prove the post-September-2025 Linux launch shape end to end. AlphaGSM launches `rocketstation_DedicatedServer.x86_64 -file start ... -logFile ./server.log -settings ... UseSteamP2P false LocalIpAddress 0.0.0.0`, the shared setup port-retry helper handles the colliding default `updateport`, and the full lifecycle passes with generic `udp` `query`, `info`, `info --json`, and clean shutdown on the managed game port.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
