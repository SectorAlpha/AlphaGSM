# Just Cause 2 Multiplayer

This guide covers the `jc2server` module in AlphaGSM.

Status: supported on Linux. The validated branch path uses AlphaGSM's shared
`steamcmd-linux` Docker runtime with the native Linux dedicated server from
Steam app `261140`. GitHub keeps one Docker-default lifecycle because the
forced process lane did not expose the managed TCP health surface.

## Quick Start

Create the server:

```bash
alphagsm myjc2server create jc2server
```

Run setup:

```bash
alphagsm myjc2server setup
```

Start it:

```bash
alphagsm myjc2server start
```

Check it:

```bash
alphagsm myjc2server status
alphagsm myjc2server query
alphagsm myjc2server info --json
```

Stop it:

```bash
alphagsm myjc2server stop
```

## Setup Details

Setup configures:

- the main game port, default `7777`
- the install directory
- anonymous SteamCMD download of the dedicated server files

AlphaGSM also keeps the native `config.lua` in sync before `start`, copying
the shipped `default_config.lua` when the install is first staged.

## Runtime Notes

- Module name: `jc2server`
- Default executable: `Jcmp-Server`
- Config file: `<install_dir>/config.lua`
- SteamCMD App ID: `261140`
- Default runtime family: `steamcmd-linux`

AlphaGSM also stages the shipped `default_scripts/` tree into `scripts/`
without overwriting user-provided scripts, so a fresh install has the stock
server logic available immediately.

## Health Contract

The validated AlphaGSM health surface is generic `tcp` on the managed main
game port.

## Useful Commands

```bash
alphagsm myjc2server update
alphagsm myjc2server backup
```

<!-- alphagsm-server-variables:start -->

## Server variables

After `create jc2server`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->
