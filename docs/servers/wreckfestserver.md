# Wreckfest

This guide covers the `wreckfestserver` module in AlphaGSM.

Status: `PASSED` for stock process and Docker startup, connectivity and shutdown
on 2026-10-14 (CI run `38545270577`). Workshop loading remains unverified.

## Workshop validation checkpoint

Native Workshop support remains under validation as of 14 October 2026.
Anonymous consumer-app `228380` downloads succeeded. Diagnostic native console
inspection listed events from the public
[Crazy 2025 track pack](https://steamcommunity.com/sharedfiles/filedetails/?id=3428792631),
including `crazy_2000_classic`, its reversed event, and its deathloop event.
The adapter preserves operator mod folders and config entries while managing
its own native `mods=` entries.

On Linux, `query` and `info` check UDP reachability on the configured query port.
They do not report track or player information. A silent UDP probe means no
port-unreachable error was received; it does not prove an application response
or measure round-trip latency. Current remote
diagnostics receive no A2S response over IPv4 or IPv6; the native server uses
THQN networking. The baseline additionally requires a fresh native
`Server connected.` log and running runtime, so reachability alone cannot pass startup.
Stock process and Docker integrations plus Docker smoke passed these checks.

Workshop checks still require fresh native track-registry output beyond the
baseline connectivity check. Automated capture and the complete modded lifecycle
remain unverified; download, configuration and old console snapshots do not
satisfy that requirement. Linux launches now give Wine a real terminal through
`script`, so native console output can reach AlphaGSM logs. Docker enables the
managed console input FIFO, with Xvfb and Wine launched once inside that
terminal. Capture snapshots the logs before sending `tracks` and accepts only
the newly appended native registry response, including its exact
`crazy_2000_classic` row. This correction still needs CI validation. Shutdown
checks include owned Wine processes and TCP/UDP port closure.

## Requirements

- Docker and AlphaGSM's `wine-proton` image for the Docker runtime on Linux
- SteamCMD access for app `361580` with anonymous login

For the process runtime on Linux, use Wine or Proton-GE, `xvfb-run`, and
`script` from the `bsdutils`/util-linux package. The runtime image includes
these tools for Docker.
The baseline integration case honors `ALPHAGSM_TEST_RUNTIME_BACKEND` from CI;
the smoke runner accepts `process`, `docker`, or `auto` through the same
variable. It defaults to Docker in GitHub Actions or when a runtime image is
provided, and to process elsewhere; explicit `auto` uses Docker.
Public Workshop checks additionally require
`ALPHAGSM_RUN_WORKSHOP=1`; baseline checks do not install a Workshop fixture.

## Quick Start

Create the server:

```bash
alphagsm mywreckfes create wreckfestserver
```

Run setup:

```bash
alphagsm mywreckfes setup
```

Start it:

```bash
alphagsm mywreckfes start
```

Check it:

```bash
alphagsm mywreckfes status
alphagsm mywreckfes query
alphagsm mywreckfes info --json
```

Stop it:

```bash
alphagsm mywreckfes stop
```

## Setup Details

Setup configures:

- the main game port (default `33540`)
- the Steam query port (default `27016`)
- the Steam networking port (default `27015`)
- the install directory
- the managed `server_config.cfg`

On Linux, AlphaGSM downloads the Windows dedicated payload for app `361580`,
launches `Wreckfest_x64.exe` through the shared Docker `wine-proton` runtime,
and seeds `server_config.cfg` from the vendor `initial_server_config.cfg` when
needed.

## Useful Commands

```bash
alphagsm mywreckfes update
alphagsm mywreckfes backup
alphagsm mywreckfes set port 33541
alphagsm mywreckfes set queryport 27017
alphagsm mywreckfes set steamport 27018
alphagsm mywreckfes set servername "AlphaGSM Wreckfest"
alphagsm mywreckfes set maxplayers 16
```

AlphaGSM keeps these upstream config keys in sync inside `server_config.cfg`:

- `game_port`
- `query_port`
- `steam_port`
- `server_name`
- `password`
- `max_players`

## Notes

- Module name: `wreckfestserver`
- Main game port default: `33540`
- Linux query/info uses the limited UDP reachability surface described above.
- Native console capture corrections remain under validation: Workshop tests
  still require the fresh engine track registry from an AlphaGSM console command.
  Neither a config echo nor an open TCP port satisfies the Workshop check.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create wreckfestserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `maxplayers` | users | integer | The maximum number of players allowed on the server. |
| `port` | gameport | integer | The main game port for the Wreckfest server. |
| `queryport` | — | integer | The Steam query port for the Wreckfest server. |
| `servername` | hostname, name | string | The advertised Wreckfest server name. |
| `serverpassword` | sv_password, password | string | Password required to join the Wreckfest server. Stored as a secret. |
| `steamport` | — | integer | The Steam networking port for the Wreckfest server. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `Wreckfest_x64.exe`
- **Fallback executable**: `Wreckfest.exe`
- **Location**: `<install_dir>/Wreckfest_x64.exe`
- **Runtime**: Docker `wine-proton` on Linux
- **SteamCMD App ID**: `361580`

### Server Configuration

- **Config file**: `server_config.cfg`
- **Vendor seed file**: `initial_server_config.cfg`
- **Template**: See [server-templates/wreckfestserver/server_config.cfg](../server-templates/wreckfestserver/server_config.cfg)

### Maps and Mods

- **Map rotation**: configure through `server_config.cfg`
- **Mod directory**: `<install_dir>/mods/`
- **Workshop support**: use Wreckfest's native mod loading rules
