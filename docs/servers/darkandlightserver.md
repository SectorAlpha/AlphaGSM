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

On Linux under Wine/Proton, AlphaGSM health checks currently fall back to a
generic UDP probe on the main game port. A fresh focused validation on
2026-05-28 reached `info --json` protocol `udp` on the managed game port, but
direct probes still showed `queryport` `27016` refusing UDP and timing out for
A2S, so the dedicated query listener is not yet usable there.

That same validation also showed why the older stop path was unsafe there:
`Ctrl-C` interrupted Proton's Python launcher and could drop the managed screen
session while leaving `DNLServer.exe` bound to the game UDP port. AlphaGSM now
targets the matched `DNLServer.exe` process directly on Linux during `stop`, so
smoke and integration coverage can verify real game-port closure rather than
just a missing screen session. Treat the module as not yet fully re-enabled on
Linux until the query-port contract is proven end to end.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/darkandlightserver/](../server-templates/darkandlightserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
