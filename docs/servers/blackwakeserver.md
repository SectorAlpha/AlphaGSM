# Blackwake

This guide covers the `blackwakeserver` module in AlphaGSM.

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
- Current validation status: PASSED 2026-05-30 on the Docker-backed `wine-proton` runtime. Fresh AlphaGSM integration and smoke now pass end to end through `create`, `setup`, `start`, `status`, `query`, `info`, `info --json`, `stop`, and post-stop verification when the server runs in the shared container image. On this validated runtime lane, `query` and `info` currently use the stable generic `tcp` health surface on the managed main port instead of the older stale A2S-on-`queryport` assumption.

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
