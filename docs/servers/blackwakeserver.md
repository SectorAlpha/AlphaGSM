# Blackwake

This guide covers the `blackwakeserver` module in AlphaGSM.

`blackwakeserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. GitHub keeps the proven shared `wine-proton` Docker lifecycle; the
game module exposes the same managed health contract without branching on the
selected runtime.

## Requirements

- Docker for the validated Linux runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- For local non-Docker launches on Linux: Wine plus `xvfb-run`

## Quick Start

Create the server:

```bash
alphagsm myblackwak create blackwakeserver
```

Run setup:

```bash
alphagsm myblackwak setup
```

Start it:

```bash
alphagsm myblackwak start
```

Check it:

```bash
alphagsm myblackwak status
```

Stop it:

```bash
alphagsm myblackwak stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the Steam query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myblackwak update
alphagsm myblackwak backup
```

## Notes

- Module name: `blackwakeserver`
- Default game port: 7777
- Default query port: 27015
- Current validation status: PASSED 2026-05-30 on the Docker-backed
  `wine-proton` runtime. `query` and `info` use the stable generic `tcp`
  health surface on the managed main port for every runtime instead of
  embedding process-versus-Docker behavior in the game module. The shared
  Docker host-resolution correction is pending replacement CI.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create blackwakeserver`, inspect or change these with `set`:

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

- **Executable**: `BlackwakeServer.exe`
- **Location**: `<install_dir>/BlackwakeServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `423410`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `54`
- **Upstream flow**: the bundled `SERVER GUIDE.txt` says the first `BlackwakeServer.exe -batchmode -nographics` launch generates `Server.cfg` and exits, and that alternate configs can be selected with `-configFile <name>`.
- **Managed defaults**: AlphaGSM syncs `serverName`, `port`, `sport`, `gamemode=7`, and a default `serverpassword` into `Server.cfg` before launch. On the validated headless Linux path it also forces `useBots=0`, because the current dedicated runtime is stable when bot crews are not spawned automatically.
- **Template**: See [server-templates/blackwakeserver/](../server-templates/blackwakeserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
