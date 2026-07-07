# Nightingale

This guide covers the `nightingale` module in AlphaGSM.

`nightingale` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `steamcmd-linux` runtime, with generic `tcp`
`query` / `info` on the managed main port.

## Requirements

- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`) for host-process installs
- Python packages from `requirements.txt`
- Docker is the preferred Linux validation path and uses the shared `steamcmd-linux` runtime image

## Quick Start

Create the server:

```bash
alphagsm mynighting create nightingale
```

Run setup:

```bash
alphagsm mynighting setup
```

Start it:

```bash
alphagsm mynighting start
```

Check it:

```bash
alphagsm mynighting status
```

Stop it:

```bash
alphagsm mynighting stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

On Linux, the validated support path is the native dedicated server inside
AlphaGSM's shared `steamcmd-linux` Docker runtime. Fresh support validation
proves:

- anonymous SteamCMD install for app `3796810`
- runtime launch through `NWXServer.sh`
- non-root container execution with the Steam bootstrap mounted into
  `~/.steam/sdk64/steamclient.so`
- `query`, `info`, and `info --json` on generic `tcp` at the managed main
  game port

## Useful Commands

```bash
alphagsm mynighting update
alphagsm mynighting backup
```

## Notes

- Module name: `nightingale`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `NWXServer.sh`
- **Location**: `<install_dir>/NWXServer.sh`
- **Engine**: Native Linux dedicated server (SteamCMD)
- **SteamCMD App ID**: `3796810`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/nightingale/](../server-templates/nightingale/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
