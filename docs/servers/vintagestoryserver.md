# Vintage Story

This guide covers the `vintagestoryserver` module in AlphaGSM.

`vintagestoryserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `steamcmd-linux` runtime, with
`dotnet VintagestoryServer.dll --dataPath <install_dir>` answering generic
`tcp` `query` / `info` on the managed game port.

## Requirements

- `screen`
- `.NET 10` runtime on process-backed hosts
- Docker runtime supported through the shared `steamcmd-linux` family image
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvintages create vintagestoryserver
```

Run setup:

```bash
alphagsm myvintages setup
```

Start it:

```bash
alphagsm myvintages start
```

Check it:

```bash
alphagsm myvintages status
```

Stop it:

```bash
alphagsm myvintages stop
```

## Setup Details

Setup configures:

- the game port (default 42420)
- the install directory
- resolves the latest stable Linux server archive by default
- downloads and extracts the server archive
- keeps the existing Docker-backed `steamcmd-linux` lane available for hosts without local `dotnet`

## Useful Commands

```bash
alphagsm myvintages update
alphagsm myvintages backup
```

You can pin a specific server build or override the archive URL during setup:

```bash
alphagsm myvintages setup --version 1.22.2
alphagsm myvintages setup --url https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.22.2.tar.gz
```

## Notes

- Module name: `vintagestoryserver`
- Default port: 42420

## Developer Notes

### Run File

- **Executable**: `VintagestoryServer.dll`
- **Location**: `<install_dir>/VintagestoryServer.dll`
- **Engine**: .NET 10 / Vintage Story dedicated server

AlphaGSM follows the upstream `server.sh` launcher contract on Linux and starts
the server with `dotnet VintagestoryServer.dll --dataPath <install_dir>`.

The validated Linux integration lane on `release_v1` is the module's existing
Docker-backed `steamcmd-linux` runtime. The checked-in integration and smoke
paths now prefer a rebuilt local `alphagsm-steamcmd-linux-runtime:test` image
when it is available, then fall back to
`ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX`, then the published
`ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest` image.

### Server Configuration

- **Config files**: `serverconfig.json`
- **Template**: See [server-templates/vintagestoryserver/](../server-templates/vintagestoryserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
