# Memories of Mars

This guide covers the `memoriesofmarsserver` module in AlphaGSM.

`memoriesofmarsserver` is disabled. [505 Games shut down Memories of Mars
online multiplayer on June 25, 2024](https://support.505games.com/support/solutions/articles/150000182159-thanks-for-the-memories),
and the retired dedicated server still depends on the removed LIMBIC session
backend. Current process and Docker launches fail to create a session and crash
before opening a query listener.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Creation is blocked with the retirement reason. The commands below document
the historical lifecycle and will apply only if an upstream-compatible server
becomes available again.

Create the server:

```bash
alphagsm mymemories create memoriesofmarsserver
```

Run setup:

```bash
alphagsm mymemories setup
```

Start it:

```bash
alphagsm mymemories start
```

Check it:

```bash
alphagsm mymemories status
```

Stop it:

```bash
alphagsm mymemories stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymemories update
alphagsm mymemories backup
```

## Notes

- Module name: `memoriesofmarsserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create memoriesofmarsserver`, inspect or change these with `set`:

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

- **Executable**: `MemoriesOfMarsServer.sh`
- **Location**: `<install_dir>/MemoriesOfMarsServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `897590`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/memoriesofmarsserver/](../server-templates/memoriesofmarsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
