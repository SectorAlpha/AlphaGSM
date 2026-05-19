# Mount & Blade II: Bannerlord

This guide covers the `bannerlordserver` module in AlphaGSM.

## Requirements

- `screen`
- `dotnet` runtime (Bannerlord launches the Linux dedicated server via `dotnet`)
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
- Docker validation no longer depends on a host-installed `dotnet`; the shared `steamcmd-linux` runtime image now carries .NET 6 for Bannerlord alongside .NET 10 for SS14.
- Bannerlord is still not green on the current Linux Docker runtime: after setup succeeds, the dedicated server exits with a native `SIGSEGV` before AlphaGSM can retrieve A2S info, and SteamCMD setup can also intermittently fail with state `0x202`.

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
