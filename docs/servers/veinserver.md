# VEIN

This guide covers the `veinserver` module in AlphaGSM.

`veinserver` is currently `PASSED` in the checked-in support tracker on the
documented Ubuntu 24.04 Linux baseline. The validated Linux lane uses the
shared `steamcmd-linux` Docker runtime, and the current GitHub integration
lane validates both process and Docker runtimes for this module while local
runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`) for host-process installs
- Python packages from `requirements.txt`
- Docker is the preferred Linux validation path and uses the shared `steamcmd-linux` runtime image

## Quick Start

Create the server:

```bash
alphagsm myveinserv create veinserver
```

Run setup:

```bash
alphagsm myveinserv setup
```

Start it:

```bash
alphagsm myveinserv start
```

Check it:

```bash
alphagsm myveinserv status
```

Stop it:

```bash
alphagsm myveinserv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the server files

On Linux, the validated support path is the native dedicated server inside
AlphaGSM's shared `steamcmd-linux` Docker runtime. Fresh support validation
proves:

- anonymous SteamCMD install for app `2131400`
- runtime launch through `VeinServer.sh`
- non-root container execution with the Steam bootstrap mounted into
  `~/.steam/sdk64/steamclient.so`
- `query`, `info`, and `info --json` on generic `tcp` at the managed main
  game port

## Useful Commands

```bash
alphagsm myveinserv update
alphagsm myveinserv backup
```

## Notes

- Module name: `veinserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `VeinServer.sh`
- **Location**: `<install_dir>/VeinServer.sh`
- **Engine**: Native Linux dedicated server (SteamCMD)
- **SteamCMD App ID**: `2131400`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/veinserver/](../server-templates/veinserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
