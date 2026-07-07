# Sniper Elite 4

This guide covers the `sniperelite4server` module in AlphaGSM.

`sniperelite4server` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- Docker for the validated Linux runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- For local non-Docker launches on Linux: Wine or Proton

## Quick Start

Create the server:

```bash
alphagsm mysniperel create sniperelite4server
```

Run setup:

```bash
alphagsm mysniperel setup
```

Start it:

```bash
alphagsm mysniperel start
```

Check it:

```bash
alphagsm mysniperel status
```

Stop it:

```bash
alphagsm mysniperel stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mysniperel update
alphagsm mysniperel backup
```

## Notes

- Module name: `sniperelite4server`
- Default game port: 7777
- Default query port: 27015
- Current validation status: PASSED 2026-05-30 on the Docker-backed
  `wine-proton` runtime. Fresh AlphaGSM integration and smoke now both pass
  through `create`, `setup`, `start`, `status`, `query`, `info`,
  `info --json`, `stop`, and post-stop verification when the server runs in
  the shared container image. On this validated Linux lane, `query` and
  `info` currently use the stable generic `tcp` health surface on the managed
  main port instead of the older stale host-log and A2S assumptions.

## Developer Notes

### Run File

- **Executable**: `bin/SniperElite4_Dedicated.exe`
- **Location**: `<install_dir>/bin/SniperElite4_Dedicated.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `568880`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `12`
- **Linux support note**: the validated Linux path now runs through AlphaGSM's
  Docker-backed `wine-proton` runtime image rather than a host `screen`
  session. AlphaGSM stages `default.cfg` in the install root before launch,
  copying the shipped `Docs/ExampleConfigs/Example1.cfg` when available so the
  dedicated server no longer aborts immediately on `default.cfg` lookup.
- **Template**: See [server-templates/sniperelite4server/](../server-templates/sniperelite4server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
