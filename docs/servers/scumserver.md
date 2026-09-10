# SCUM

This guide covers the `scumserver` module in AlphaGSM.

## Support Status

- Status: `PASSED`
- Validated on Linux through the shared Docker `wine-proton` runtime
- Anonymous SteamCMD app id: `3792580`

AlphaGSM now supports SCUM on Linux by installing the Windows dedicated
payload through anonymous SteamCMD and running the real server binary under the
shared Wine/Proton runtime. The validated AlphaGSM health surface on this lane
is generic `tcp` on the managed main game port.

## Quick Start

Create the server:

```bash
alphagsm myscumserv create scumserver
```

Run setup:

```bash
alphagsm myscumserv setup
```

Start it:

```bash
alphagsm myscumserv start
```

Check it:

```bash
alphagsm myscumserv query
alphagsm myscumserv info --json
alphagsm myscumserv status
```

Stop it:

```bash
alphagsm myscumserv stop
```

## Setup Details

Setup configures:

- the game port, default `7777`
- the raw UDP port, default `port + 1`
- the query port, default `port + 2`
- the install directory
- anonymous SteamCMD download for app `3792580`

On Linux, AlphaGSM uses the shared `wine-proton` Docker runtime for the
supported path. GitHub CI runs one Docker-default heavy lifecycle rather than
also forcing a host-process Wine lane that currently stays alive without
opening the managed health port.

## Runtime Contract

- Executable: `SCUM/Binaries/Win64/SCUMServer.exe`
- Working directory: `<install_dir>`
- Primary config dir: `<install_dir>/SCUM/Saved/Config/WindowsServer/`
- Primary log: `<install_dir>/SCUM/Saved/Logs/SCUM.log`
- Query/info surface: generic `tcp` on the managed main game port

The validated launch contract is:

```text
SCUM/Binaries/Win64/SCUMServer.exe -log -port=<port> -QueryPort=<queryport> -MaxPlayers=<maxplayers>
```

## Useful Commands

```bash
alphagsm myscumserv set queryport 27020
alphagsm myscumserv set maxplayers 64
alphagsm myscumserv update
alphagsm myscumserv backup
```

## Notes

- Module name: `scumserver`
- SteamCMD app id: `3792580`
- Supported Linux path: Docker `wine-proton`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create scumserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `maxplayers` | users | integer | The maximum number of players. Example: `16`. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |
| `queryport` | — | integer | The query port for the server. Example: `27015`. |

<!-- alphagsm-server-variables:end -->
