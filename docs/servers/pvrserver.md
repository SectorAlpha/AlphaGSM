# Pavlov VR

This guide covers the `pvrserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`, `libc++1`)
- Python packages from `requirements.txt`

On Ubuntu 24.04, Pavlov VR still requests the unversioned `libc++.so` runtime
name. The shared AlphaGSM images create a compatibility symlink to
`libc++.so.1`; on a host install, do the same after installing `libc++1`:

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
- the query port (default 7778)
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
- Default query port: 7778

## Developer Notes

### Run File

- **Executable**: `PavlovServer.sh`
- **Location**: `<install_dir>/PavlovServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `622970`

Smoke and integration validation track readiness through `alphagsm info --json`
returning protocol `a2s` on the query port instead of waiting for screen-log
markers.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/pvrserver/](../server-templates/pvrserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
