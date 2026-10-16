# Natural Selection 2

This guide covers the `ns2server` module in AlphaGSM.

The checked-in Natural Selection 2 lifecycle is wired for both process and
Docker runtimes on the documented Ubuntu 24.04 Linux baseline. Its corrected
launch/A2S contract is pending replacement GitHub validation, so no new
`PASSED` tracker result is recorded for this change.

## Requirements

- Process runtime: `screen`
- Docker runtime: Docker and the shared `steamcmd-linux` runtime image
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myns2 create ns2server
```

Run setup:

```bash
alphagsm myns2 setup
```

Start it:

```bash
alphagsm myns2 start
```

Check it:

```bash
alphagsm myns2 status
alphagsm myns2 query
alphagsm myns2 info
```

Stop it:

```bash
alphagsm myns2 stop
```

## Setup Details

Setup configures:

- the game port (default `27015`)
- the install directory
- SteamCMD downloads the server files
- a per-instance config directory at `<install_dir>/<server_name>/`
- a workshop storage directory at `<install_dir>/<server_name>/Workshop`
- a managed log directory at `<install_dir>/logs`
- managed claims for game UDP, `game + 1` UDP, web-admin TCP, and mod-server
  TCP

## Useful Commands

```bash
alphagsm myns2 update
alphagsm myns2 backup
```

## Notes

- Module name: `ns2server`
- Game: Natural Selection 2
- Engine: Spark
- SteamCMD App ID: `4940`
- Executable: `<install_dir>/x64/server_linux`
- Default map: `ns2_summit`
- Process and Docker launch identical game argv as `./x64/server_linux` from
  the install root, with relative config, log, and workshop paths
- AlphaGSM probes exact runtime-resolved A2S on `game port + 1`
- Web admin is enabled by default on `httpport` `8080`
- Mod server is enabled by default on `modserverport` `27031`
- Current correction status: replacement GitHub validation pending

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ns2server`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `httppassword` | — | string | Web admin password. |
| `httpport` | — | integer | Web admin port. |
| `httpuser` | — | string | Web admin username. |
| `maxplayers` | users | integer | Maximum allowed players. |
| `maxspectators` | — | integer | Maximum allowed spectators. |
| `modserveraddress` | — | string | Optional owned local interface for the native mod download web server. |
| `modserverport` | — | integer | Mod server port. |
| `port` | gameport | integer | Primary gameplay port. |
| `servername` | hostname, name | string | The advertised server name. |
| `startmap` | map, gamemap, level, world | string | Startup map. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `x64/server_linux`
- **Location**: `<install_dir>/x64/server_linux`
- **Working directory**: `<install_dir>`
- **Launch path**: `./x64/server_linux`
- **Engine**: Spark
- **SteamCMD App ID**: `4940`

### Server Configuration

- **Config path**: `<install_dir>/<server_name>/`
- **Workshop storage**: `<install_dir>/<server_name>/Workshop`
- **Log directory**: `<install_dir>/logs`
- **Runtime argv paths**: `./<server_name>`, `./logs`, and
  `./<server_name>/Workshop`
- **Key settings**:
  - `port` — Game port (default: `27015`)
  - `httpport` — Web admin port (default: `8080`)
  - `webdomain` — Optional web admin bind address (engine default: `localhost`)
  - `modserverport` — Mod server port (default: `27031`)
  - `maxplayers` — Maximum players (default: `20`)
  - `maxspectators` — Maximum spectators (default: `5`)
  - `startmap` — Starting map (default: `ns2_summit`)

### Maps and Mods

- **Map selection**: via `startmap`
- **Mod directory**: `<install_dir>/<server_name>/Workshop`
- **Workshop support**: native mod activation through hexadecimal IDs in MapCycle.json.


## Native Workshop multiplayer content

```bash
alphagsm myns2 mod add workshop 129599221
alphagsm myns2 mod add workshop-collection YOUR_COLLECTION_ID
alphagsm myns2 mod apply
alphagsm myns2 start
```

Official Steam Community item and collection URLs work too. AlphaGSM validates
consumer AppID `4920`, expands collections, and merges hexadecimal mod IDs into
`<install_dir>/<server_name>/MapCycle.json`. The same native IDs are passed with
`-mods`, and NS2 downloads and mounts the content itself. No Steam account or
Workshop API key is supplied. Apply while stopped; prestart also reconciles the
managed list unless `mods.autoapply` is false.

Existing map rotations, settings, operator mod IDs and other JSON fields remain.
`mod cleanup` removes unchanged owned mod IDs; it retains operator edits and
engine-managed Workshop caches. Symlinks, invalid JSON and unsafe native IDs fail
before a write. Native storage stays under the per-server install directory,
including server names containing hyphens.

The native mod file server can need an explicit local interface behind NAT:
`alphagsm myns2 set modserveraddress YOUR_OWNED_LAN_IP`. Its native port is
`modserverport`; the public IP is not necessarily a bindable local address.
The validation uses loopback for this local-only download endpoint; remote-client
content delivery has not been verified.

Web admin also listens on `localhost` by default. `webdomain` accepts an owned
local interface IP; Spark rejects the wildcard `0.0.0.0`. The Docker Workshop
check reads the same authenticated native API on loopback inside AlphaGSM's
managed container, using its installed Python. It keeps admin on loopback and
still requires exact native map origin, map-change execution and external A2S.

The opt-in check downloads public [ns2_Jambi](https://steamcommunity.com/sharedfiles/filedetails/?id=129599221),
starts on a stock map, waits for the real engine web API, requests the custom map
through web admin, and requires both custom-map A2S and `Server.GetMapModId`
attribution through `getmaplist`. File existence alone cannot satisfy it.
The native Workshop process and Docker lifecycles passed in GitHub CI run
`38655040006` on 2026-10-15, including the Docker loopback API transport.

```bash
ALPHAGSM_WORK_DIR=/path/on/large/disk \
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_NS2SERVER_WORKSHOP=1 \
python3 -m pytest tests/integration_tests/test_ns2server.py -k workshop

ALPHAGSM_WORK_DIR=/path/on/large/disk NS2_WORKSHOP_ITEM=129599221 \
make smoke-test SMOKE_TEST=run_ns2server.sh
```

Collection overrides use `ALPHAGSM_NS2SERVER_WORKSHOP_COLLECTION`, with
`ALPHAGSM_NS2SERVER_WORKSHOP_LOAD_ITEM` and `ALPHAGSM_NS2SERVER_WORKSHOP_MAP` selecting
the map to exercise. Smoke uses corresponding `NS2_WORKSHOP_*` variables. Keep
web-admin credentials private and configure your own password before public use.
