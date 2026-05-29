# Pavlov VR

This guide covers the `pvrserver` module in AlphaGSM.

## Requirements

- Docker for the primary validated runtime path
- `screen` only if you intentionally run the legacy host-process path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`, `libc++1`)
- Python packages from `requirements.txt`

On current Ubuntu 24.04 hosts, Pavlov VR's Linux dedicated binary needs the
LLVM C++ runtime on the host process path and will fail before readiness if
`libc++.so.1` is missing. The shared AlphaGSM `steamcmd-linux` Docker image
already provides this runtime, so the current smoke and integration lifecycle
validation for `pvrserver` should run on the Docker runtime backend first. For
host-process runs, install `libc++1` first.

Some host installs may also still need the unversioned `libc++.so` loader
name, so keep the compatibility symlink in place after installing `libc++1`:

```bash
sudo apt install libc++1
sudo ln -sf /lib/x86_64-linux-gnu/libc++.so.1 /lib/x86_64-linux-gnu/libc++.so
```

## Quick Start

Create the server:

```bash
alphagsm mypvrserve create pvrserver
```

Run setup:

```bash
alphagsm mypvrserve setup
```

Start it:

```bash
alphagsm mypvrserve start
```

Check it:

```bash
alphagsm mypvrserve status
```

Stop it:

```bash
alphagsm mypvrserve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the status/query helper port (fixed at game port + 400, so 8177 by default)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypvrserve update
alphagsm mypvrserve backup
```

## Notes

- Module name: `pvrserver`
- Default game port: 7777
- Default status/query helper port: 8177

## Developer Notes

### Run File

- **Executable**: `PavlovServer.sh`
- **Location**: `<install_dir>/PavlovServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `622970`

Smoke and integration validation now track readiness through `alphagsm info --json`
returning protocol `udp` on Pavlov's status-helper port (`port + 400`) instead
of waiting for screen-log markers, and the supported validation path uses the
`steamcmd-linux` Docker runtime image rather than the host process path.

Focused validation on 2026-05-29 proved that the current Docker-primary path is
materially better than the older host-process lane. AlphaGSM now tolerates the
known SteamCMD false-negative where app `622970` reports `state is 0x602 after
update job` even though `PavlovServer.sh` is already present, and the supported
runtime path uses the `steamcmd-linux` Docker image plus the runtime-aware stop
hook for graceful `alphagsm stop`.

The remaining follow-up is now narrower and operational instead of protocol
fiction: the checked-in module/tests/docs are aligned to the generic UDP helper
port contract, but this refreshed Docker-first lifecycle still needs another
full end-to-end rerun before the server can be promoted out of the disabled
bucket.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/pvrserver/](../server-templates/pvrserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
