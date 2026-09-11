# Colony Survival

This guide covers the `colserver` module in AlphaGSM.

`colserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `steamcmd-linux` runtime, with generic `udp`
`query` / `info` on the managed `queryport`.

## Requirements

- Docker for the validated Linux runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycolserve create colserver
```

Run setup:

```bash
alphagsm mycolserve setup
```

Start it:

```bash
alphagsm mycolserve start
```

Check it:

```bash
alphagsm mycolserve status
```

Stop it:

```bash
alphagsm mycolserve stop
```

## Setup Details

Setup configures:

- the game port (default 27005)
- the query port (`queryport`) one lower than the game port by default
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycolserve update
alphagsm mycolserve backup
```

## Notes

- Module name: `colserver`
- Validated Linux path: Docker `steamcmd-linux` runtime
- Default game port: `27005`
- Default query port: `27004`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create colserver`, inspect or change these with `set`:

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

- **Executable**: `ColonyServer.x86_64`
- **Location**: `<install_dir>/ColonyServer.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `748090`

### Server Configuration

- **Config files**: `server.config.json`
- **Max players**: `16`
- **Template**: See [server-templates/colserver/](../server-templates/colserver/) if available
- **Health surface**: generic `udp` on the managed `queryport`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
