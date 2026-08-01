# ASTRONEER

This guide covers the `astroneerserver` module in AlphaGSM.

`astroneerserver` is `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline because registration validation requires an externally routable
endpoint. The checked-in Linux validation path is Docker-first through the
shared `wine-proton` runtime plus in-container Xvfb; CI explicitly reports the
test as skipped when that external endpoint is not configured.

## Requirements

- Docker recommended on Linux: branch-local or published `alphagsm-wine-proton-runtime`
- Host/process fallback: `screen` plus a working Wine/Proton install
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- An externally routable IPv4 address for Astroneer registration

## Quick Start

Create the server:

```bash
alphagsm myastronee create astroneerserver
```

Run setup:

```bash
alphagsm myastronee setup
```

Before starting, set the real public IPv4 address players use to reach this
server. This is separate from AlphaGSM's local process/Docker query routing.

```bash
alphagsm myastronee set registration_publicip "<externally-routable-ipv4>"
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
- the owner identity (`AlphaGSM` by default)
- the install directory
- SteamCMD downloads the server files
- AlphaGSM syncs the port and `net.AllowEncryption=False` into
  `WindowsServer/Engine.ini`, and the ownership values into
  `WindowsServer/AstroServerSettings.ini`

`registration_publicip` must be a globally routable IPv4 address before
`start`. AlphaGSM rejects blank, loopback, private, and non-IPv4 values rather
than launching a dedicated server that immediately rewrites its registration
settings and exits.

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
- Current correction status: replacement GitHub validation pending. The
  Docker smoke and integration cases run in the configurable heavy GitHub
  Actions lane. That runner must expose the managed UDP port through the
  address in the `ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP` repository variable.
- ASTRONEER's Windows-only server needs `net.AllowEncryption=False` for the
  supported Wine/Proton path. Players joining from a Windows or Proton client
  must set the same value in that client's Astroneer `Engine.ini`.

## Developer Notes

### Run File

- **Executable**: `Astro/Binaries/Win64/AstroServer-Win64-Shipping.exe`
- **Location**: `<install_dir>/Astro/Binaries/Win64/AstroServer-Win64-Shipping.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `728470`
- **Docker runtime note**: the shared `wine-proton` entrypoint selects Proton, matching the process runtime, and starts Xvfb so the bundled UE4 prerequisite bootstrap can complete instead of aborting on `Failed to create window`
- **Launcher note**: AlphaGSM launches the dedicated-server shipping executable directly from `Astro/Binaries/Win64`, preserving Unreal's relative engine-content paths. Existing configurations that still name the root `AstroServer.exe` launcher are migrated at launch when the shipping executable is present.
- **Failure diagnostics**: strict readiness failures record the Docker exit state,
  container command, safe runtime-selection environment, process table, and
  managed `Engine.ini` plus `AstroServerSettings.ini` before cleanup. The smoke
  path also records the non-secret registration fields immediately after setup,
  before the game process can rewrite them.

The readiness marker comes from ASTRONEER's own log rather than a host
`screen` log. After that marker names the managed port, AlphaGSM resolves the
selected runtime host and performs generic UDP query/info checks on that exact
main-port endpoint. `registration_publicip` is written only to Astroneer's
`AstroServerSettings.ini`; it never changes that runtime-local query endpoint.

### Server Configuration

- **Config file**: See game module source
- **Managed files**: `Astro/Saved/Config/WindowsServer/Engine.ini` and
  `AstroServerSettings.ini`
- **Managed keys**: `port`, `registration_publicip`, `ownername`; Engine
  compatibility also keeps `net.AllowEncryption=False`
- **Legacy configuration**: a pre-existing `publicip` is read only as a
  migration fallback when `registration_publicip` is unset. New configurations
  should use `registration_publicip`, leaving `publicip` available for generic
  runtime routing.
- **Template**: See [server-templates/astroneerserver/](../server-templates/astroneerserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
