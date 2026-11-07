# Just Cause 3 Multiplayer

This guide covers the `jc3server` module in AlphaGSM.

Status: supported on Linux. The validated branch path uses AlphaGSM's shared
`steamcmd-linux` Docker runtime with the native Linux dedicated server from
Steam app `619960`.

## Quick Start

Create the server:

```bash
alphagsm myjc3server create jc3server
```

Run setup:

```bash
alphagsm myjc3server setup
```

Start it:

```bash
alphagsm myjc3server start
```

Check it:

```bash
alphagsm myjc3server status
alphagsm myjc3server query
alphagsm myjc3server info --json
```

Stop it:

```bash
alphagsm myjc3server stop
```

## Setup Details

Setup configures:

- the main game port, default `4200`
- the install directory
- anonymous SteamCMD download of the dedicated server files

AlphaGSM also keeps the native `config.json` in sync before `start`.

## Port Contract

AlphaGSM manages the native JC3MP side ports from the configured main port:

- `port = <game port>`
- `queryPort = port + 1`
- `steamPort = port + 2`
- `httpPort = port + 3`

The validated AlphaGSM health surface is generic `tcp` on `httpPort`.

## Runtime Notes

- Module name: `jc3server`
- Default executable: `Server`
- Config file: `<install_dir>/config.json`
- SteamCMD App ID: `619960`
- Default runtime family: `steamcmd-linux`

## Useful Commands

```bash
alphagsm myjc3server update
alphagsm myjc3server backup
```

<!-- alphagsm-server-variables:start -->

## Server variables

After `create jc3server`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->
