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
wrapper with SDL `x11` plus software GL. A fresh focused rerun then confirmed
the config-sync fix: AlphaGSM's managed test port now lands in
`dedicated_server_config.json` before startup. The remaining blocker is still
runtime readiness under the current Wine/Proton path: in the fresh host run,
`start` returned success and left `TT2Server.exe` running, but the server never
created `Saved/Logs/TT2.log`, never opened the configured listener on the
managed port, and the only captured screen-log output was ProtonFixes
"Skipping fix execution. We are probably running a unit test." warnings before
the 600 second readiness timeout. Keep this server in the validation queue
until the launch path produces the expected `TT2.log` and real A2S readiness.

### Server Configuration

- **Config files**: `dedicated_server_config.json`
- **Template**: See [server-templates/terratechworldsserver/](../server-templates/terratechworldsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
