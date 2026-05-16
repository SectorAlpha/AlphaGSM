# Team Fortress 2 Classified

This guide covers the `tf2cserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD and the 32-bit Source runtime libraries it needs
- Python packages from `requirements.txt`

TF2C requires a separate live Team Fortress 2 dedicated-server install for its
base files. AlphaGSM manages that automatically by downloading app `232250`
into a support directory and then launching TF2C with `-tf_path`.

## Quick Start

Create the server:

```bash
alphagsm mytf2c create tf2cserver
```

Run setup:

```bash
alphagsm mytf2c setup
```

Start it:

```bash
alphagsm mytf2c start
```

Check it:

```bash
alphagsm mytf2c status
```

Stop it:

```bash
alphagsm mytf2c stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the client port (default 27005)
- the SourceTV port (default 27020)
- the install directory
- a TF2 support directory rooted at `<install_dir>/tf`

## Notes

- Module name: `tf2cserver`
- LinuxGSM-compatible aliases: `tf2c`, `tf2classified`, `tf2classifiedserver`
- TF2C Steam App ID: `3557020`
- Base TF2 Steam App ID: `232250`
- Default map: `4koth_frigid`

## Developer Notes

### Run File

- **Executable**: `srcds.sh`
- **Location**: `<install_dir>/srcds.sh`
- **Engine**: Source
- **SteamCMD App ID**: `3557020`
- **Base install**: `<install_dir>/tf` is passed to the server as `-tf_path`

### Server Configuration

- **Config file**: `tf2classified/cfg/server.cfg`
- **Template**: AlphaGSM writes the native Source `server.cfg` on install/setup

### Maps and Mods

- **Map directory**: `tf2classified/maps/`
- **Addon directory**: `tf2classified/addons/`
- **Workshop support**: No

Smoke and integration validation track readiness through `alphagsm info --json`
returning protocol `a2s` on the main Source query endpoint.