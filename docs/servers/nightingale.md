# Nightingale

This guide covers the `nightingale` module in AlphaGSM.

`nightingale` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `steamcmd-linux` runtime. The current branch
uses Nightingale's official HTTP `/status` endpoint for `query` / `info` on
the managed status port. Its Docker launch uses host networking because the
current native server keeps that status listener on container loopback.

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
- the HTTP status port (default 7778)
- the install directory
- SteamCMD downloads the server files

On Linux, the validated support path is the native dedicated server inside
AlphaGSM's shared `steamcmd-linux` Docker runtime. Fresh support validation
proves:

- anonymous SteamCMD install for app `3796810`
- runtime launch through `NWXServer.sh`
- non-root container execution with the Steam bootstrap mounted into
  `~/.steam/sdk64/steamclient.so`
- `NWXServer.sh -port=<port> -statusPort=<queryport>`
- host networking so the server's loopback-bound HTTP status listener remains
  reachable to AlphaGSM
- `query`, `info`, and `info --json` through JSON `/status` on `queryport`
- smoke validation allows ten minutes for first-world generation and navigation
  data before requiring the HTTP status to report ready

## Useful Commands

```bash
alphagsm mynighting update
alphagsm mynighting backup
```

## Notes

- Module name: `nightingale`
- Default port: 7777
- Default status/query port: 7778
- Nightingale retains the documented listener override in its launch arguments;
  current Linux builds still expose `/status` only through loopback in CI.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create nightingale`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

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
