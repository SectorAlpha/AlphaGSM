# DeadPoly

This guide covers the `deadpolyserver` module in AlphaGSM.

## Support Status

- Status: `PASSED`
- Validated on Linux through the shared Docker `wine-proton` runtime
- Anonymous SteamCMD app id: `2208380`

AlphaGSM now supports DeadPoly on Linux by installing the Windows dedicated
payload through anonymous SteamCMD and running the real server binary under the
shared Wine/Proton runtime. The validated health surface is generic `tcp` on
the managed `queryport`.

## Quick Start

Create the server:

```bash
alphagsm mydeadpoly create deadpolyserver
```

Run setup:

```bash
alphagsm mydeadpoly setup
```

Start it:

```bash
alphagsm mydeadpoly start
```

Check it:

```bash
alphagsm mydeadpoly query
alphagsm mydeadpoly info --json
alphagsm mydeadpoly status
```

Stop it:

```bash
alphagsm mydeadpoly stop
```

## Setup Details

Setup configures:

- the game port, default `7777`
- the query port, default `7778`
- the install directory
- anonymous SteamCMD download for app `2208380`

On Linux, AlphaGSM uses the shared `wine-proton` Docker runtime for the
supported path.

## Runtime Contract

- Executable: `DeadPolyServer.exe`
- Fallback executable: `DeadPoly/Binaries/Win64/DeadPolyServer.exe`
- Working directory: `<install_dir>`
- Config seed: `<install_dir>/DeadPoly/Saved/1 RENAME Config`
- Managed config: `<install_dir>/DeadPoly/Saved/Config/WindowsServer/Game.ini`
- Query/info surface: generic `tcp` on `queryport`

Before start, AlphaGSM stages the shipped `1 RENAME Config` tree into
`DeadPoly/Saved/Config` when needed and syncs:

- `servername`
- `maxplayers`

The validated launch contract is:

```text
DeadPolyServer.exe -log -nosteam -port=<port> -queryport=<queryport> -maxplayers=<maxplayers>
```

## Useful Commands

```bash
alphagsm mydeadpoly set servername "My DeadPoly Server"
alphagsm mydeadpoly set maxplayers 32
alphagsm mydeadpoly set queryport 27020
alphagsm mydeadpoly update
alphagsm mydeadpoly backup
```

## Notes

- Module name: `deadpolyserver`
- SteamCMD app id: `2208380`
- Supported Linux path: Docker `wine-proton`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create deadpolyserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `maxplayers` | users | integer | The maximum number of players. |
| `port` | gameport | integer | The game port for the server. |
| `queryport` | — | integer | The query port for the server. |
| `servername` | hostname, name | string | The advertised server name. |

<!-- alphagsm-server-variables:end -->
