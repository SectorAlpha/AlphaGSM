# FOUNDRY

This guide covers the `foundryserver` module in AlphaGSM.

`foundryserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that staged-server prerequisite,
while local runs remain process-backed by default unless you opt into the
Docker backend.

## Requirements

- `screen`
- `wine` and `xvfb-run` on Linux
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfoundrys create foundryserver
```

Run setup:

```bash
alphagsm myfoundrys setup
```

`foundryserver` is supported in `ENABLED (BYO)` mode. Anonymous SteamCMD app
`2915550` downloads the Windows dedicated server (`FoundryDedicatedServer.exe`).
There is no native Linux depot. On Linux, AlphaGSM launches that executable
with Wine and `xvfb-run`. A staged tree in `<install_dir>/` is only needed
when that anonymous download cannot supply the executable.

A local process run on 2026-10-16 answered A2S on UDP 27016, with game port
51535 (`Procedural`, hostname AlphaGSM lafoundryserver, 0/32) and stopped.
UDP 27015 was already in use, so setup selected 27016. Docker was not rerun.

Start it:

```bash
alphagsm myfoundrys start
```

Check it:

```bash
alphagsm myfoundrys status
```

Stop it:

```bash
alphagsm myfoundrys stop
```

## Setup Details

Setup configures:

- the game port (default 37200)
- the Steam query port (default 27015)
- the install directory

Before each start, AlphaGSM writes `app.cfg` next to `FoundryDedicatedServer.exe`.
That file keeps `server_is_public=true`, sets `pause_server_when_empty=false`,
and sets `server_query_port` to the query port. It also writes `steam_appid.txt`
with the game client id `983870`, which is what the official launcher writes.
FOUNDRY answers Steam A2S only when the server is public, and the query port
is separate from the game port. The default query port is 27015. If that port
is already in use, setup chooses the next free port instead of the game port.
`alphagsm <server-name> query` uses that existing A2S port. Change the query
port with `alphagsm <server-name> set queryport <port>`. A `server_password`
already in `app.cfg` is left in place.

Suggested flow:

```bash
alphagsm myfoundrys create foundryserver
alphagsm myfoundrys setup -n 37200 /path/to/foundry
alphagsm myfoundrys start
```

## Useful Commands

```bash
alphagsm myfoundrys update
alphagsm myfoundrys backup
```

## Notes

- Module name: `foundryserver`
- Default game port: 37200
- Default query port: 27015 (`server_query_port` in `app.cfg`), or the next free port when 27015 is busy
- A2S requires `server_is_public=true`: https://dedicated.foundry-game.com/

<!-- alphagsm-server-variables:start -->

## Server variables

After `create foundryserver`, inspect or change these with `set`:

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

- **Executable**: `FoundryDedicatedServer.exe`
- **Location**: `<install_dir>/FoundryDedicatedServer.exe`
- **Engine**: Custom (SteamCMD, Windows build; Wine on Linux)
- **SteamCMD App ID**: `2915550`
- **Steam client App ID**: `983870` (`steam_appid.txt`)

### Server Configuration

- **Config file**: `<install_dir>/app.cfg`
- **Template**: See [server-templates/foundryserver/](../server-templates/foundryserver/) if available
- **Query**: Steam A2S on `queryport` after `server_is_public=true`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
This helper checks known sentinels only and directs you to stage the complete
compatible distribution manually; managed import is unavailable for this recipe.
See [BYO files and private SteamCMD acquisition](../byo-files.md).
