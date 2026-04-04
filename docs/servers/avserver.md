# Avorion

This guide covers the `avserver` module in AlphaGSM.

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

```bash
alphagsm myavserver update
alphagsm myavserver backup
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
- **Mod directory**: Check game documentation
- **Workshop support**: No
