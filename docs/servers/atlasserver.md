# ATLAS

This guide covers the `atlasserver` module in AlphaGSM.

## Requirements

- `docker` for the checked-in smoke/integration validation path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`, `libprotobuf10`, `libidn11`, and `libldap-2.4-2` compatibility packages)
- The shared `steamcmd-linux` runtime image for the default validated path, or a legacy OpenSSL 1.0.x compatible host runtime for `libssl.so.1.0.0` if you intentionally launch the native Linux binary outside Docker
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myatlasser create atlasserver
```

Run setup:

```bash
alphagsm myatlasser setup
```

Start it:

```bash
alphagsm myatlasser start
```

Check it:

```bash
alphagsm myatlasser status
```

Stop it:

```bash
alphagsm myatlasser stop
```

## Setup Details

Setup configures:

- the game port (default 57555)
- the query port (default 57561)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myatlasser update
alphagsm myatlasser backup
```

## Notes

- Module name: `atlasserver`
- Default game port: 57555
- Default query port: 57561

## Developer Notes

### Run File

- **Executable**: `ShooterGame/Binaries/Linux/ShooterGameServer`
- **Location**: `<install_dir>/ShooterGame/Binaries/Linux/ShooterGameServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1006030`

Smoke and integration validation track readiness through `alphagsm info --json`
returning protocol `a2s` on the dedicated query port via AlphaGSM's resolved
local query host instead of relying on implicit fallback routing. The checked-in
validation path now opts into the module's existing `steamcmd-linux` Docker
runtime hooks, which carry the legacy ATLAS compatibility libraries that the
native Linux binary is missing on current Ubuntu 24.04 hosts.

For Docker-backed launches, AlphaGSM now seeds `steam_appid.txt` and an
install-local `.steam/sdk64/steamclient.so` link inside the mounted server
directory, then exports `HOME=/srv/server` plus an install-local
`LD_LIBRARY_PATH` inside the container. That keeps the ATLAS binary from
depending on host-only SteamCMD home-directory state when the validated runtime
path runs in Docker.

Host-process launches are still available for environments that provide
`libssl.so.1.0.0`, but they are no longer the default validation path. If you
intentionally run ATLAS outside Docker on a modern host and the binary exits
immediately, check for `error while loading shared libraries: libssl.so.1.0.0`
before debugging the AlphaGSM lifecycle itself.

If a Docker-backed lifecycle still dies before `info --json` reports `a2s`,
inspect the earliest server log lines for `SteamAPI_Init()` /
`SteamAPI_IsSteamRunning()` before assuming the failure is in AlphaGSM query or
stop handling.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/atlasserver/](../server-templates/atlasserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
