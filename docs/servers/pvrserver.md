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
- the status/query port (fixed at game port + 400, so 8177 by default)
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
- Default status/query port: 8177

## Developer Notes

### Run File

- **Executable**: `PavlovServer.sh`
- **Location**: `<install_dir>/PavlovServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `622970`

Smoke and integration validation track readiness through `alphagsm info --json`
returning protocol `a2s` on Pavlov's status-helper port (`port + 400`) instead
of waiting for screen-log markers, and the supported validation path now uses
the `steamcmd-linux` Docker runtime image rather than the host process path.

Focused host validation on 2026-05-28 proved that the longer 60 minute setup
budget is enough for Pavlov VR's 9.17 GB SteamCMD payload. The next proven
host-process blocker is missing `libc++.so.1`: AlphaGSM's shared local-runtime
dependency gate now fails fast with a clear dependency error instead of
returning success and only leaving the loader failure in the screen log, and it
recommends installing `libc++1` when you need a local process run. The primary
supported runtime path is the Docker/runtime-image flow, which already carries
the needed libc++ runtime and now uses the module's runtime-aware stop hook for
graceful `alphagsm stop`.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/pvrserver/](../server-templates/pvrserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
