# Dark and Light

This guide covers the `darkandlightserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydarkandl create darkandlightserver
```

Run setup:

```bash
alphagsm mydarkandl setup
```

Start it:

```bash
alphagsm mydarkandl start
```

Check it:

```bash
alphagsm mydarkandl status
```

Stop it:

```bash
alphagsm mydarkandl stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27016)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mydarkandl update
alphagsm mydarkandl backup
```

## Notes

- Module name: `darkandlightserver`
- Default game port: 7777
- Default query port: 27016

## Developer Notes

### Run File

- **Executable**: `DNL/Binaries/Win64/DNLServer.exe`
- **Location**: `<install_dir>/DNL/Binaries/Win64/DNLServer.exe`
- **Engine**: UE4 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `630230`

On Linux under Wine/Proton, the current branch no longer reaches even the
narrowed generic-UDP contract. A fresh focused rerun on 2026-05-28 showed
`alphagsm start` returning success, but the managed `screen` session died
before `info --json` ever reported UDP readiness, `DNL/Saved/Logs/DNL.log` was
never created, and direct host probes saw both the managed game port and
`queryport` `27016` refuse UDP traffic.

Direct repro of AlphaGSM's current Proton launch command kept
`DNLServer.exe DNL_ALL?...?Port=<game-port>?QueryPort=27016 -nullRHI -log -unattended`
alive for at least 90 seconds with no console output beyond the ProtonFixes
"Skipping fix execution. We are probably running a unit test." warnings, still
without creating `DNL.log` or binding either managed UDP listener. Because the
`screen` session is already gone in that state, `alphagsm stop` refuses with
`Can't stop a server that isn't running`, so the Linux stop hook cannot clean
up the orphaned `DNLServer.exe` automatically. Treat the module as blocked on
Linux until startup proves a real listener and a live AlphaGSM-managed session
again.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/darkandlightserver/](../server-templates/darkandlightserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
