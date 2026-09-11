# CryoFall

This guide covers the `cryofallserver` module in AlphaGSM.

## Support Status

- Status: `PASSED`
- Validated on Linux through the shared Docker `steamcmd-linux` runtime
- Anonymous SteamCMD app id: `1061710`

AlphaGSM now supports CryoFall on Linux with the native `.NET 6` dedicated
server payload delivered by anonymous SteamCMD. The validated health surface is
generic `udp` on the managed main game port.

## Quick Start

Create the server:

```bash
alphagsm mycryofall create cryofallserver
```

Run setup:

```bash
alphagsm mycryofall setup
```

Start it:

```bash
alphagsm mycryofall start
```

Check it:

```bash
alphagsm mycryofall query
alphagsm mycryofall info --json
alphagsm mycryofall status
```

Stop it:

```bash
alphagsm mycryofall stop
```

## Setup Details

Setup configures:

- the game port, default `6000`
- the install directory
- anonymous SteamCMD download for app `1061710`

On Linux, AlphaGSM uses the shared `steamcmd-linux` Docker runtime for the
validated path.

## Runtime Contract

- Executable: `Binaries/Server/CryoFall_Server.dll`
- Runtime: `dotnet`
- Working directory: `<install_dir>`
- Config file: `<install_dir>/Data/SettingsServer.xml`
- Query/info surface: generic `udp` on the managed main port

Before start, AlphaGSM stages and syncs:

- `port`
- `servername`
- `maxplayers`

AlphaGSM launches the dedicated server with the required world mode:

```text
dotnet Binaries/Server/CryoFall_Server.dll loadOrNew
```

## Useful Commands

```bash
alphagsm mycryofall set servername "My CryoFall Server"
alphagsm mycryofall set maxplayers 32
alphagsm mycryofall update
alphagsm mycryofall backup
```

## Notes

- Module name: `cryofallserver`
- SteamCMD app id: `1061710`
- Supported Linux path: Docker `steamcmd-linux`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create cryofallserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->
