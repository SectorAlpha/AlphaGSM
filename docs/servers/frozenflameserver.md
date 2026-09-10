# Frozen Flame

This guide covers the `frozenflameserver` module in AlphaGSM.

`frozenflameserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Validation of the Docker host-user change is pending CI; local runs use the process runtime unless you select Docker.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfrozenfl create frozenflameserver
```

Run setup:

```bash
alphagsm myfrozenfl setup
```

Start it:

```bash
alphagsm myfrozenfl start
```

Check it:

```bash
alphagsm myfrozenfl status
```

Stop it:

```bash
alphagsm myfrozenfl stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myfrozenfl update
alphagsm myfrozenfl backup
```

## Notes

- Module name: `frozenflameserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create frozenflameserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `port` | gameport | integer | The game port for the server. Example: `7777`. |
| `queryport` | — | integer | The query port for the server. Example: `27015`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `FrozenFlameServer.sh`
- **Location**: `<install_dir>/FrozenFlameServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1348640`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/frozenflameserver/](../server-templates/frozenflameserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
