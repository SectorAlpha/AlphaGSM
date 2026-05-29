# Longvinter

This guide covers the `longvinterserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylongvint create longvinterserver
```

Run setup:

```bash
alphagsm mylongvint setup
```

Start it:

```bash
alphagsm mylongvint start
```

Check it:

```bash
alphagsm mylongvint status
```

Stop it:

```bash
alphagsm mylongvint stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylongvint update
alphagsm mylongvint backup
```

## Notes

- Module name: `longvinterserver`
- Default port: 7777
- Current CI status: still disabled. The older AlphaGSM lane expects `LongvinterServer.sh` plus a dedicated query-port contract, but current upstream Linux guidance has moved on to a native binary contract and does not yet provide a fresh end-to-end AlphaGSM lifecycle proof.

## Developer Notes

### Run File

- **Historical AlphaGSM executable**: `LongvinterServer.sh`
- **Current upstream Linux entrypoint**: `Longvinter/Binaries/Linux/LongvinterServer-Linux-Shipping`
- **Observed modern Steam launch args**: `-log`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1639880`

Current blocker status on 2026-05-29 is more precise than the older packaged-script crash note:

- the current public Steam app advertises a native Linux launch entrypoint at `Longvinter/Binaries/Linux/LongvinterServer-Linux-Shipping -log`, not the older shell-wrapper contract,
- the current official wiki documents Linux setup around `Game.ini` plus optional `-GamePort`,
- the older Docker guide is explicitly deprecated,
- AlphaGSM is still wired to the stale launcher/query assumptions, so there is no fresh honest proof yet for the modern Linux runtime/query contract.

Until the module is reconciled with that current upstream Linux contract and revalidated through `create -> setup -> start -> query -> info -> stop`, the disabled gate should stay in place.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/longvinterserver/](../server-templates/longvinterserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
