# HumanitZ

This guide covers the `hzserver` module in AlphaGSM.

## Support Status

- Status: `PASSED`
- Validated on Linux through the shared Docker `wine-proton` runtime
- Anonymous SteamCMD app id: `2728330`

AlphaGSM now supports HumanitZ on Linux by installing the Windows dedicated
payload through SteamCMD and running the real Win64 server binary under the
shared Wine/Proton runtime. The validated health surface is generic `udp` on
the managed `queryport`.

## Quick Start

Create the server:

```bash
alphagsm myhzserver create hzserver
```

Run setup:

```bash
alphagsm myhzserver setup
```

Start it:

```bash
alphagsm myhzserver start
```

Check it:

```bash
alphagsm myhzserver query
alphagsm myhzserver info --json
alphagsm myhzserver status
```

Stop it:

```bash
alphagsm myhzserver stop
```

## Setup Details

Setup configures:

- the game port, default `7777`
- the query port, default `27016`
- the install directory
- anonymous SteamCMD download for app `2728330`

On Linux, AlphaGSM uses the shared `wine-proton` Docker runtime for the
supported path.

## Runtime Contract

- Executable: `HumanitZServer/Binaries/Win64/HumanitZServer-Win64-Shipping.exe`
- Working directory: `<install_dir>`
- Config file: `<install_dir>/HumanitZServer/GameServerSettings.ini`
- Reference config: `<install_dir>/HumanitZServer/REF_GameServerSettings.ini`
- Query/info surface: generic `udp` on `queryport`

Before start, AlphaGSM stages `GameServerSettings.ini` from the shipped
reference config when needed and syncs:

- `servername`
- `maxplayers`

## Useful Commands

```bash
alphagsm myhzserver set servername "My HumanitZ Server"
alphagsm myhzserver set maxplayers 24
alphagsm myhzserver set queryport 27020
alphagsm myhzserver update
alphagsm myhzserver backup
```

## Notes

- Module name: `hzserver`
- SteamCMD app id: `2728330`
- Supported Linux path: Docker `wine-proton`
