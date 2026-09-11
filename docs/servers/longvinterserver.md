# Longvinter

This guide covers the `longvinterserver` module in AlphaGSM.

`longvinterserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- Docker for the validated `steamcmd-linux` runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylongvint create longvinterserver
```

Run setup:

```bash
alphagsm mylongvint setup
```

Start it:

```bash
alphagsm mylongvint start
```

Check it:

```bash
alphagsm mylongvint status
```

Stop it:

```bash
alphagsm mylongvint stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- `Longvinter/Saved/Config/LinuxServer/Game.ini`
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylongvint update
alphagsm mylongvint backup
```

## Notes

- Module name: `longvinterserver`
- Default port: 7777
- Current CI status: passed on 2026-05-29. Fresh smoke and integration now
  pass on the Docker-backed `steamcmd-linux` runtime path.
- `query`, `info`, and `info --json` use generic UDP reachability on the main
  game port, not a separate A2S `queryport`.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create longvinterserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `maxplayers` | users | integer | Maximum allowed players. |
| `port` | gameport | integer | Primary gameplay port. |
| `servername` | hostname, name | string | Configured public server name. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **AlphaGSM executable**: `LongvinterServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1639880`
- **Validated runtime**: Docker-backed `steamcmd-linux`
- **Validated launch path**: `./LongvinterServer.sh -Port=<port>`
- **Docker note**: the Linux dedicated binary refuses to run as root, so the
  container path now drops to the mounted server-directory owner before launch.

### Server Configuration

- **Config file**: `Longvinter/Saved/Config/LinuxServer/Game.ini`
- **Max players**: `32`
- **Managed keys**: `servername`, `maxplayers`
- **Template**: See [server-templates/longvinterserver/](../server-templates/longvinterserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
