# Avorion

This guide covers the `avserver` module in AlphaGSM.

`avserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myavserver create avserver
```

Run setup:

```bash
alphagsm myavserver setup
```

Start it:

```bash
alphagsm myavserver start
```

Check it:

```bash
alphagsm myavserver status
```

Stop it:

```bash
alphagsm myavserver stop
```

## Setup Details

Setup configures:

- the game port (default 27000)
- the internal query port (default `port + 3`)
- the Steam query and master ports (defaults `port + 20` and `port + 21`)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

Workshop items and collections accept numeric IDs or Steam Community URLs. The
dedicated server and public Workshop content use anonymous Steam access.

```bash
alphagsm myavserver mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=1722652757
alphagsm myavserver mod add workshop-collection COLLECTION_ID_OR_URL
alphagsm myavserver mod list
alphagsm myavserver mod apply
alphagsm myavserver mod remove workshop 1722652757
alphagsm myavserver mod apply
alphagsm myavserver mod cleanup
```

Apply downloads and validates native `modinfo.lua` metadata, then adds the
Workshop IDs to the configured galaxy's `modconfig.lua`. Add each required
Workshop dependency to desired state; AlphaGSM validates dependency versions and
orders prerequisites first. Avorion checks compatibility with its own game
version at startup. Client-only packages and executable metadata are refused.
Metadata must use ordinary literal Lua tables.

Setup, update and start reapply desired state by default. Restart after changing
mods. Existing operator Lua is preserved; cleanup clears desired items and
removes only AlphaGSM's unchanged configuration block. Externally edited managed
blocks cause a clear refusal. The managed download cache remains available.
Changing `galaxy` moves the managed block to that galaxy on the next apply.

```bash
alphagsm myavserver update
alphagsm myavserver backup
```

The optional smoke fixture is [AzimuthLib](https://steamcommunity.com/sharedfiles/filedetails/?id=1722652757).
On 13 October 2026, the process and Docker Workshop lifecycle tests downloaded it
anonymously and executed its native `getInt` function through Avorion's console.
The tests also checked `query`, `info`, JSON output and complete shutdown. These
health commands use UDP reachability, so native library execution is the separate
proof that Workshop content loaded.

```bash
ALPHAGSM_RUN_WORKSHOP=1 bash tests/smoke_tests/run_avserver.sh
ALPHAGSM_RUN_WORKSHOP=1 ALPHAGSM_TEST_RUNTIME_BACKEND=process bash tests/smoke_tests/run_avserver.sh
```

## Notes

- Module name: `avserver`
- Default port: 27000
- Default query port: 27003
- Default Steam query port: 27020
- Default Steam master port: 27021
- AlphaGSM starts Avorion with `--datapath ./galaxies` so galaxy state stays under the install directory
- AlphaGSM `query` and `info` use generic UDP reachability on the Steam query port
- The `administration` datastore key is optional and maps to Avorion's `--admin` CLI argument, not an `admin.xml` file path

<!-- alphagsm-server-variables:start -->

## Server variables

After `create avserver`, inspect or change these with `set`:

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

- **Executable**: `server.sh`
- **Location**: `<install_dir>/server.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `565060`
- **Headless launch**: `./server.sh --datapath ./galaxies --galaxy-name <name> --server-name <name> --port <port> --query-port <port+3> --steam-query-port <port+20> --steam-master-port <port+21>`

### Server Configuration

- **Galaxy data path**: `<install_dir>/galaxies/<galaxy-name>`
- **Template**: See [server-templates/avserver/](../server-templates/avserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Native mod configuration**: `<install_dir>/galaxies/<galaxy-name>/modconfig.lua`
- **Workshop consumer App ID**: `445220` (dedicated-server App ID: `565060`)
- **Workshop support**: Native multiplayer mods through anonymous Steam access
