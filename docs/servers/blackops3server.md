# Call of Duty: Black Ops III

This guide covers the `blackops3server` module in AlphaGSM.

`blackops3server` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. GitHub validates the Windows server through the shared
`wine-proton` Docker runtime in the heavy test partition.

## Requirements

- Docker
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myblackops create blackops3server
```

Run setup:

```bash
alphagsm myblackops setup
```

Start it:

```bash
alphagsm myblackops start
```

Check it:

```bash
alphagsm myblackops status
```

Stop it:

```bash
alphagsm myblackops stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- a consecutive managed three-port group mapped to container ports
  `27015`, `27016`, and `27017`
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myblackops update
alphagsm myblackops backup
```

## Notes

- Module name: `blackops3server`
- Default port: 27015
- The launch follows the shipped unranked-server command without an ineffective
  custom `-port` switch.
- Readiness combines `CreateDedicatedModsLobby: ready!` with AlphaGSM generic
  UDP `query` / `info` on the managed base port.
- The active Docker smoke and integration correction is pending replacement CI.

## Developer Notes

### Run File

- **Executable**: `UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe`
- **Location**: `<install_dir>/UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe`
- **Engine**: Windows dedicated server through Wine/Proton
- **SteamCMD App ID**: `545990`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `18`
- **Template**: See [server-templates/blackops3server/](../server-templates/blackops3server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
