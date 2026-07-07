# ATLAS

This guide covers the `atlasserver` module in AlphaGSM.

`atlasserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The checked-in validation path is Docker-first because the
shared `steamcmd-linux` runtime image carries the compatibility stack this
server still expects, and the current GitHub integration lane exercises both
process and Docker runtime selection around the staged server-grid export
prerequisite.

## Requirements

- `docker` for the checked-in smoke/integration validation path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`, `libprotobuf10`, `libidn11`, and `libldap-2.4-2` compatibility packages)
- The shared `steamcmd-linux` runtime image for the default validated path, or a legacy OpenSSL 1.0.x compatible host runtime for `libssl.so.1.0.0` if you intentionally launch the native Linux binary outside Docker
- Python packages from `requirements.txt`
- A staged ATLAS server-grid export: `ServerGrid.json`, `ServerGrid.ServerOnly.json`, and the `ServerGrid/` folder

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

## Support Status

`atlasserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install and
launch the dedicated payload, but ATLAS still requires an operator-supplied
server-grid export before `start` can finish booting a world.

Stage these under `<install_dir>/ShooterGame/` before `start`:

- `ServerGrid.json`
- `ServerGrid.ServerOnly.json`
- `ServerGrid/`

These files are typically generated with the official ATLAS ServerGridEditor.

## Setup Details

Setup configures:

- the game port (default 57555)
- the query port (default 57561)
- the install directory
- SteamCMD downloads the server files
- `start` still requires the staged ATLAS server-grid export under `ShooterGame/`

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

For Docker-backed launches, AlphaGSM now mounts the shared Steam bootstrap
payload into the container, runs the server as a non-root `alphagsm` user, and
launches `ShooterGameServer` from `ShooterGame/Binaries/Linux` instead of the
install root. That keeps the validated Docker runtime from depending on
host-only Steam home-directory state and avoids the earlier launch-contract
crash path.

Host-process launches are still available for environments that provide
`libssl.so.1.0.0`, but they are no longer the default validation path. If you
intentionally run ATLAS outside Docker on a modern host and the binary exits
immediately, check for `error while loading shared libraries: libssl.so.1.0.0`
before debugging the AlphaGSM lifecycle itself.

If ATLAS still exits early after the grid export is staged, inspect
`ShooterGame/Saved/Logs/ShooterGame.log` first. A missing
`ServerGrid.ServerOnly.json` or `ServerGrid/` export is now the primary known
operator-side blocker, not missing Linux compatibility libraries.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/atlasserver/](../server-templates/atlasserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
- **Current status**: Supported in `ENABLED (BYO)` mode. Before `start`,
  generate/export `ServerGrid.json`, `ServerGrid.ServerOnly.json`, and the
  `ServerGrid/` folder with the official ATLAS ServerGridEditor and copy them
  into `<install_dir>/ShooterGame/`.
