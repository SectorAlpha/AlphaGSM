# Sunkenland

This guide covers the `sunkenlandserver` module in AlphaGSM.

`sunkenlandserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- Wine or Proton-GE on Linux
- `xvfb-run` on Linux process runtimes
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysunkenla create sunkenlandserver
```

Run setup:

```bash
alphagsm mysunkenla setup
```

Start it:

```bash
alphagsm mysunkenla start
```

Check it:

```bash
alphagsm mysunkenla status
```

Stop it:

```bash
alphagsm mysunkenla stop
```

## Setup Details

Setup configures:

- the game port (default 29000)
- the configured query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysunkenla update
alphagsm mysunkenla backup
```

## Notes

- Linux process launches require `xvfb-run` to provide the display used during
  Wine initialization. The shared Wine/Proton Docker image supplies it when
  using the Docker runtime.
- Module name: `sunkenlandserver`
- Default game port: 29000
- Default query port: 27015
- `query`, `info`, and `info --json` use the validated TCP health surface on
  the managed game port.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create sunkenlandserver`, inspect or change these with `set`:

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

- **Executable**: `Sunkenland-DedicatedServer.exe`
- **Location**: `<install_dir>/Sunkenland-DedicatedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2667530`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/sunkenlandserver/](../server-templates/sunkenlandserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
