# TerraTech Worlds

This guide covers the `terratechworldsserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myterratec create terratechworldsserver
```

Run setup:

```bash
alphagsm myterratec setup
```

Start it:

```bash
alphagsm myterratec start
```

Check it:

```bash
alphagsm myterratec status
```

Stop it:

```bash
alphagsm myterratec stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myterratec update
alphagsm myterratec backup
```

## Notes

- Module name: `terratechworldsserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `TT2Server.exe`
- **Location**: `<install_dir>/TT2Server.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2533070`

AlphaGSM launches the server with `-log -nullrhi`, tracks readiness through
`Saved/Logs/TT2.log`, and waits for `info --json` to report protocol `a2s`
before treating the server as query-ready.

Current validation status: the 2026-05-28 follow-up switched the module to the
official dedicated launch flags (`-log -nullrhi`) and a headless `xvfb-run`
wrapper with SDL `x11` plus software GL. The next bounded fix was wiring
AlphaGSM's configured `port` into `dedicated_server_config.json`; existing
validation artifacts showed the Windows dedicated server was still inheriting
its default `Port` `7777` even when AlphaGSM had claimed a different test
port. A full live rerun was still in SteamCMD setup at report time, so keep
this server in the validation queue until the post-fix Wine/Unity startup path
is rechecked against `Saved/Logs/TT2.log` and A2S readiness.

### Server Configuration

- **Config files**: `dedicated_server_config.json`
- **Template**: See [server-templates/terratechworldsserver/](../server-templates/terratechworldsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
