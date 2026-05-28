# Mount & Blade II: Bannerlord

This guide covers the `bannerlordserver` module in AlphaGSM.

## Requirements

- `docker` for the supported validation path on `release_v1`
- host `dotnet` only if you intentionally run the legacy process-backed path outside Docker
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybannerlo create bannerlordserver
```

Run setup:

```bash
alphagsm mybannerlo setup
```

Start it:

```bash
alphagsm mybannerlo start
```

Check it:

```bash
alphagsm mybannerlo status
```

Stop it:

```bash
alphagsm mybannerlo stop
```

## Setup Details

Setup configures:

- the game port (default 7210)
- the install directory
- SteamCMD downloads the server files
- AlphaGSM launches the Linux starter from `bin/Linux64_Shipping_Server/`

## Useful Commands

```bash
alphagsm mybannerlo update
alphagsm mybannerlo backup
```

## Notes

- Module name: `bannerlordserver`
- Default port: 7210
- Anonymous SteamCMD installs for app `1863440` do succeed; the stale disabled gate was caused by the module pointing at a nonexistent root executable instead of the installed Linux starter.
- The current Linux launch path is `dotnet TaleWorlds.Starter.DotNetCore.Linux.dll` from `bin/Linux64_Shipping_Server/`.
- The supported validation path on `release_v1` is the module's existing `steamcmd-linux` Docker runtime. The checked-in smoke and integration runners now prefer the branch-local `alphagsm-steamcmd-linux-runtime:bannerlord-dotnet` image when it is present, then fall back to `ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX`, then the published `ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest` image.
- On this branch, the published `ghcr.io/...:latest` image on the current host still fails earlier with `exec: "dotnet": executable file not found in $PATH`, so it does not prove the real Bannerlord lifecycle here.
- The branch-local Docker image gets to the real server runtime, but Bannerlord is still not green there: after setup succeeds and `dotnet --info` confirms `.NET 6.0.36`, `dotnet TaleWorlds.Starter.DotNetCore.Linux.dll ...` segfaults immediately and the managed container exits `139` before AlphaGSM can reach A2S `query` or `info`.

## Developer Notes

### Run File

- **Executable**: `TaleWorlds.Starter.DotNetCore.Linux.dll`
- **Location**: `<install_dir>/bin/Linux64_Shipping_Server/TaleWorlds.Starter.DotNetCore.Linux.dll`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1863440`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/bannerlordserver/](../server-templates/bannerlordserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
