# Blackwake

This guide covers the `blackwakeserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

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

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myblackwak update
alphagsm myblackwak backup
```

## Notes

- Module name: `blackwakeserver`
- Default port: 27015
- Current validation status: still not enabled on Linux/Wine as of 2026-05-28. The managed startup path now writes `Server.cfg`, disables bots by default with a managed password, and targets the declared Steam query port, but the dedicated process still exits after startup with repeated `BotHandler` exceptions before `query` / `info` become ready.

## Developer Notes

### Run File

- **Executable**: `BlackwakeServer.exe`
- **Location**: `<install_dir>/BlackwakeServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `423410`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `54`
- **Managed defaults**: AlphaGSM now syncs `serverName`, `port`, `sport`, and a default `serverpassword` into `Server.cfg` before launch. On the current headless Linux/Wine path it also forces `useBots=0` to avoid the earlier immediate bot-spawn crash path.
- **Template**: See [server-templates/blackwakeserver/](../server-templates/blackwakeserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
