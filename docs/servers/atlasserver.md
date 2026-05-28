# ATLAS

This guide covers the `atlasserver` module in AlphaGSM.

## Requirements

- `screen` for the current host-process smoke/integration path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`, `libprotobuf10`, `libidn11`, and `libldap-2.4-2` compatibility packages)
- A legacy OpenSSL 1.0.x compatible runtime for `libssl.so.1.0.0` on current Linux hosts when launching the native Linux binary outside the shared Docker runtime
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
local query host instead of relying on implicit fallback routing.

`atlasserver` already exposes the shared `steamcmd-linux` runtime hooks, and
that shared Docker runtime family carries the legacy ATLAS compatibility
libraries. The remaining blocker on this host class is narrower: the checked-in
ATLAS smoke/integration path still validates the host-process `screen` launch,
and on current Ubuntu 24.04 hosts `ldconfig -p` exposes `libssl.so.1.1` but
not `libssl.so.1.0.0`. As a result, `ShooterGameServer` exits immediately with
`error while loading shared libraries: libssl.so.1.0.0` before AlphaGSM can
reach the A2S readiness/query contract.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/atlasserver/](../server-templates/atlasserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
