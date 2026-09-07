# Squad 44

This guide covers the `squad44server` module in AlphaGSM.

`squad44server` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Validation of the Docker host-user change is pending CI; local runs use the process runtime unless you select Docker.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysquad44s create squad44server
```

Run setup:

```bash
alphagsm mysquad44s setup
```

Start it:

```bash
alphagsm mysquad44s start
```

Check it:

```bash
alphagsm mysquad44s status
```

Stop it:

```bash
alphagsm mysquad44s stop
```

## Setup Details

Setup configures:

- the game port (default 27165)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysquad44s update
alphagsm mysquad44s backup
```

## Notes

- Module name: `squad44server`
- Default port: 27165

## Developer Notes

### Run File

- **Executable**: `PostScriptumServer.sh`
- **Location**: `<install_dir>/PostScriptumServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `746200`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/squad44server/](../server-templates/squad44server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
