# HogWarp

This guide covers the `hogwarpserver` module in AlphaGSM.

`hogwarpserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that archive-or-staged-tree
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- either a direct HogWarp dedicated-server archive URL or a pre-staged
  HogWarp Windows server tree
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhogwarps create hogwarpserver
```

Run setup:

```bash
alphagsm myhogwarps setup
```

HogWarp is supported in `ENABLED (BYO)` mode in AlphaGSM. Before `setup` or
`start`, either:

- set `url` to a direct HogWarp dedicated-server archive, or
- stage `HogWarpServer.exe` and the rest of the HogWarp server files inside
  your chosen `<install_dir>/`

Start it:

```bash
alphagsm myhogwarps start
```

Check it:

```bash
alphagsm myhogwarps status
```

Stop it:

```bash
alphagsm myhogwarps stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive when `url` is set

Suggested flow:

```bash
alphagsm myhogwarps create hogwarpserver
alphagsm myhogwarps set url https://example.invalid/hogwarp-server.zip
alphagsm myhogwarps setup -n 7777 /path/to/hogwarp
alphagsm myhogwarps start
```

Or, if you already have the Windows server files:

```bash
alphagsm myhogwarps create hogwarpserver
alphagsm myhogwarps setup -n 7777 /path/to/hogwarp
# copy HogWarpServer.exe and the rest of the server tree into /path/to/hogwarp/
alphagsm myhogwarps start
```

## Useful Commands

```bash
alphagsm myhogwarps update
alphagsm myhogwarps backup
alphagsm myhogwarps set url https://example.invalid/hogwarp-server.zip
```

## Notes

- Module name: `hogwarpserver`
- Default port: 7777

<!-- alphagsm-server-variables:start -->

## Server variables

After `create hogwarpserver`, inspect or change these with `set`:

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

- **Executable**: `HogWarpServer.exe`
- **Location**: `<install_dir>/HogWarpServer.exe`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/hogwarpserver/](../server-templates/hogwarpserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
