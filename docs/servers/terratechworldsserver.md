# TerraTech Worlds

This guide covers the `terratechworldsserver` module in AlphaGSM.

`terratechworldsserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection, and the validated Linux path remains
Wine/Proton-backed with generic `udp` lifecycle checks on the managed game
port.

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

<!-- alphagsm-server-variables:start -->

## Server variables

After `create terratechworldsserver`, inspect or change these with `set`:

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

- **Executable**: `TT2Server.exe` launcher on Windows; AlphaGSM's Linux lane now
  bypasses it and launches `TT2/Binaries/Win64/TT2Server-Win64-Shipping.exe`
  directly under Wine.
- **Location**: `<install_dir>/TT2Server.exe` and
  `<install_dir>/TT2/Binaries/Win64/TT2Server-Win64-Shipping.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2533070`

AlphaGSM launches the Windows dedicated binary with `-log`, tracks readiness
through `TT2/Saved/Logs/TT2.log`, and treats `info --json` protocol `udp` on
the managed game port as the readiness contract.

Current validation status: the 2026-05-28 follow-up tightened the Linux launch
contract after proving that the root `TT2Server.exe` bootstrap path stalls in a
headless SDL/Xalia UI layer before the real server starts. A focused live probe
against the inner `TT2Server-Win64-Shipping.exe` under `xvfb-run` plus Wine
created `TT2/Saved/Logs/TT2.log`, reached `LogNet: ... listening on port 7777`,
and responded to AlphaGSM's generic UDP probe while A2S and TCP both failed.

A fresh end-to-end AlphaGSM rerun on 2026-05-28 now passes on that direct
binary UDP contract. Anonymous SteamCMD setup for app `2533070` completed, the
managed AlphaGSM port (`52707` in the focused run) synced into
`dedicated_server_config.json`, `TT2/Saved/Logs/TT2.log` reached `Created
socket for bind address: 0.0.0.0:52707`, `IpNetDriver listening on port
52707`, and `Bringing World ...`, and AlphaGSM `status`, `query`, `info`, and
`info --json` all succeeded with protocol `udp` before a clean `stop`. This
lane is ready for parent tracker/changelog promotion from validation queue to
passed on the generic UDP contract.

### Server Configuration

- **Config files**: `dedicated_server_config.json`
- **Template**: See [server-templates/terratechworldsserver/](../server-templates/terratechworldsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
