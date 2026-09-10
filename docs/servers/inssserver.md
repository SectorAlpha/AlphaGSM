# Insurgency: Sandstorm

This guide covers the `inssserver` module in AlphaGSM.

`inssserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Validation of the Docker host-user change is pending CI; local runs use the process runtime unless you select Docker.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myinssserv create inssserver
```

Run setup:

```bash
alphagsm myinssserv setup
```

Start it:

```bash
alphagsm myinssserv start
```

Check it:

```bash
alphagsm myinssserv status
```

Stop it:

```bash
alphagsm myinssserv stop
```

## Setup Details

Setup configures:

- the game port (default 27131)
- the query port (default `port + 1`)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myinssserv update
alphagsm myinssserv backup
```

## Notes

- Module name: `inssserver`
- Default game port: 27131
- Default query port: `port + 1`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create inssserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `gslt` | — | string | Optional game server login token. |
| `hostname` | servername, name | string | Server hostname shown in the browser. |
| `mapcycle` | — | string | Initial scenario or mapcycle entry. |
| `maxplayers` | users | integer | Maximum allowed players. |
| `port` | gameport | integer | Primary gameplay port. |
| `queryport` | — | integer | Steam query port. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `InsurgencyServer-Linux-Shipping`
- **Location**: `<install_dir>/InsurgencyServer-Linux-Shipping`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `581330`

Smoke and integration validation wait for the startup log and then require
`alphagsm info --json` to report `a2s` on the Sandstorm query path.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `28`
- **Template**: See [server-templates/inssserver/](../server-templates/inssserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
