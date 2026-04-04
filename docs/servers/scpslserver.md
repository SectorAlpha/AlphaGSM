# SCP: Secret Laboratory

This guide covers the `scpslserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myscpslser create scpslserver
```

Run setup:

```bash
alphagsm myscpslser setup
```

Start it:

```bash
alphagsm myscpslser start
```

Check it:

```bash
alphagsm myscpslser status
```

Stop it:

```bash
alphagsm myscpslser stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default `port + 1`)
- the install directory
- optional `contactemail` for the public-list contact field
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myscpslser update
alphagsm myscpslser backup
```

## Notes

- Module name: `scpslserver`
- Default port: 7777
- AlphaGSM launches SCP:SL through `LocalAdmin`, not by invoking `SCPSL.x86_64` directly
- AlphaGSM seeds `home/.config/SCP Secret Laboratory/` inside the server install so the EULA/config wizard stays noninteractive
- Query is enabled in the generated gameplay config, with `query_port_shift: 1`

## Developer Notes

### Run File

- **Executable**: `LocalAdmin`
- **Location**: `<install_dir>/LocalAdmin`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `996560`

### Server Configuration

- **Config root**: `<install_dir>/home/.config/SCP Secret Laboratory/`
- **Gameplay config**: `<install_dir>/home/.config/SCP Secret Laboratory/config/<port>/config_gameplay.txt`
- **Optional property**: `contactemail` maps to SCP:SL `contact_email`
- **Template**: See [server-templates/scpslserver/](../server-templates/scpslserver/) if available
- **Current status**: The dedicated server can be launched headlessly on Linux through `LocalAdmin` once its EULA/config state is preseeded.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
