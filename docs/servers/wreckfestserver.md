# Wreckfest

This guide covers the `wreckfestserver` module in AlphaGSM.

Status: `PASSED` on 2026-05-31.

## Workshop validation checkpoint

Native Workshop support remains under validation as of 13 October 2026.
Anonymous consumer-app `228380` downloads succeeded, and the actual engine's
`tracks` command registered the public
[Crazy 2025 track pack](https://steamcommunity.com/sharedfiles/filedetails/?id=3428792631),
including `crazy_2000_classic`, its reversed event, and its deathloop event.
The adapter preserves operator mod folders and config entries while managing
its own native `mods=` entries.

The complete modded process lifecycle still fails at genuine Steam A2S
query/info readiness, including with query ports in the vendor's LAN discovery
range. AlphaGSM now checks that native query port; a listening Docker TCP proxy
cannot establish server health. A diagnostic native Windows console probe
proved track registration, but no console query fallback is exposed yet.
Linux process launch now uses Xvfb consistently with Docker; owned Wine-child
shutdown remains part of final verification. Workshop Docker checks are
pending the test host's SSD-backed Docker endpoint. The historical baseline
status above does not establish Workshop lifecycle support.

## Requirements

- Docker and AlphaGSM's `wine-proton` image for the Docker runtime on Linux
- SteamCMD access for app `361580` with anonymous login

For the process runtime on Linux, use Wine or Proton-GE and `xvfb-run`.
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
- Query/info requires an actual Steam A2S response on the configured query port.
- Wine console input/output remains a validation limitation: the native
  Windows console can register the Workshop track, while ordinary AlphaGSM
  stdin/log capture has not yet supplied that native command response.
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
