# Return to Moria

This guide covers the `returntomoriaserver` module in AlphaGSM.

Status: PASSED on 2026-05-29
The validated Ubuntu 24.04 path is one Docker-default `wine-proton` lifecycle.
The current Proton preference, readiness, and redacted-diagnostics correction
is pending replacement GitHub CI and does not record a new pass.
Both the process command wrapper and Docker container specification prefer the
same Proton launch policy, so the game module does not choose a different
Windows compatibility path based on the selected runtime.

## Requirements

- Docker
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myreturnto create returntomoriaserver
```

Run setup:

```bash
alphagsm myreturnto setup
```

Start it:

```bash
alphagsm myreturnto start
```

Check it:

```bash
alphagsm myreturnto status
```

Stop it:

```bash
alphagsm myreturnto stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files
- AlphaGSM writes `MoriaServerConfig.ini` before first launch and keeps `ListenPort`,
  `AdvertiseAddress`, and the world name aligned with the managed datastore
- readiness first follows `Moria/Saved/Config/Status.json` reporting `running`,
  then AlphaGSM validates the exact managed runtime-resolved `udp` port through
  `info --json`

## Useful Commands

```bash
alphagsm myreturnto update
alphagsm myreturnto backup
```

## Notes

- Module name: `returntomoriaserver`
- Default port: 7777
- `query`, `info`, and `info --json` use generic UDP reachability on the managed game port
- the default `AdvertiseAddress` is `local`; for internet-hosted servers set it to `auto`
  or your public IP before sharing the server externally
- readiness failures print redacted managed-runtime diagnostics. Invite and
  join codes from `Status.json` are not retained in failure state or output.

## Developer Notes

### Run File

- **Executable**: `MoriaServer.exe`
- **Location**: `<install_dir>/MoriaServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3349480`

### Server Configuration

- **Config files**: `MoriaServerConfig.ini`
- **Runtime status file**: `Moria/Saved/Config/Status.json` is the game-owned
  readiness gate used by smoke and integration tests before the same lifecycle
  validates AlphaGSM's runtime-resolved UDP health surface
- **Template**: See [server-templates/returntomoriaserver/](../server-templates/returntomoriaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
