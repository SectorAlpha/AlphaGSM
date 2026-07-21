# ASTRONEER

This guide covers the `astroneerserver` module in AlphaGSM.

`astroneerserver` retains its prior `PASSED` status from 2026-05-29 on the
documented Ubuntu 24.04 Linux baseline. The current protocol/readiness
correction is pending replacement GitHub validation and does not record a new
pass. The checked-in Linux validation path is Docker-first through the shared
`wine-proton` runtime plus in-container Xvfb.

## Requirements

- Docker recommended on Linux: branch-local or published `alphagsm-wine-proton-runtime`
- Host/process fallback: `screen` plus a working Wine/Proton install
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myastronee create astroneerserver
```

Run setup:

```bash
alphagsm myastronee setup
```

Start it:

```bash
alphagsm myastronee start
```

Check it:

```bash
alphagsm myastronee status
```

Stop it:

```bash
alphagsm myastronee stop
```

## Setup Details

Setup configures:

- the game port (default 8777)
- the public IP and owner identity
- the install directory
- SteamCMD downloads the server files
- AlphaGSM syncs the port and `net.AllowEncryption=False` into
  `WindowsServer/Engine.ini`, and the ownership values into
  `WindowsServer/AstroServerSettings.ini`

## Useful Commands

```bash
alphagsm myastronee update
alphagsm myastronee backup
```

## Notes

- Module name: `astroneerserver`
- Default port: 8777
- Current supported validation lane: Docker runtime on Linux
- Readiness first requires `IpNetDriver listening on port <managed port>` in
  the game-owned `Astro/Saved/Logs/*.log`
- `query`, `info`, and `info --json` then use the exact runtime-resolved generic
  UDP endpoint on the managed main port
- The runtime claims and publishes only the managed UDP game port
- Current correction status: replacement GitHub validation pending
- ASTRONEER's Windows-only server needs `net.AllowEncryption=False` for the
  supported Wine/Proton path. Players joining from a Windows or Proton client
  must set the same value in that client's Astroneer `Engine.ini`.

## Developer Notes

### Run File

- **Executable**: `AstroServer.exe`
- **Location**: `<install_dir>/AstroServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `728470`
- **Docker runtime note**: the shared `wine-proton` entrypoint selects Proton, matching the process runtime, and starts Xvfb so the bundled UE4 prerequisite bootstrap can complete instead of aborting on `Failed to create window`
- **Failure diagnostics**: strict readiness failures record the container command,
  safe runtime-selection environment, process table, and managed `Engine.ini`
  before cleanup

The readiness marker comes from ASTRONEER's own log rather than a host
`screen` log. After that marker names the managed port, AlphaGSM resolves the
selected runtime host and performs generic UDP query/info checks on that exact
main-port endpoint.

### Server Configuration

- **Config file**: See game module source
- **Managed files**: `Astro/Saved/Config/WindowsServer/Engine.ini` and
  `AstroServerSettings.ini`
- **Managed keys**: `port`, `publicip`, `ownername`; Engine compatibility also
  keeps `net.AllowEncryption=False`
- **Template**: See [server-templates/astroneerserver/](../server-templates/astroneerserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
