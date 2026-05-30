# GTA FiveM

This guide covers the `gtafivemserver` module in AlphaGSM.

## Requirements

- `screen`
- a Cfx.re server license key
- operator-managed txAdmin or vanilla `server-data` provisioning
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygtafivem create gtafivemserver
```

Run setup:

```bash
alphagsm mygtafivem setup
```

`gtafivemserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can download the
current Linux FXServer artifact, but you still need to complete one of the
supported Cfx provisioning flows before the server is actually ready:

- txAdmin first-run provisioning against the downloaded artifact, including
  browser-based account linking, PIN entry, and recipe/profile creation, or
- a pre-staged vanilla `server-data/` tree with a valid `server.cfg`, license
  key, resources, and any other server configuration you intend to run

Start it:

```bash
alphagsm mygtafivem start
```

Check it:

```bash
alphagsm mygtafivem status
```

Stop it:

```bash
alphagsm mygtafivem stop
```

## Setup Details

Setup configures:

- the game port (default 30120)
- the install directory
- downloads and extracts the server archive

Suggested txAdmin-oriented flow:

```bash
alphagsm mygtafivem create gtafivemserver
alphagsm mygtafivem setup -n 30120 /path/to/fivemserver
alphagsm mygtafivem start
# complete txAdmin provisioning in the browser against the downloaded artifact
```

Suggested vanilla/server-data flow:

```bash
alphagsm mygtafivem create gtafivemserver
alphagsm mygtafivem setup -n 30120 /path/to/fivemserver
# stage your server-data tree with server.cfg and sv_licenseKey
alphagsm mygtafivem start
```

## Useful Commands

```bash
alphagsm mygtafivem update
alphagsm mygtafivem backup
```

## Notes

- Module name: `gtafivemserver`
- Default port: 30120
- Install mode: `ENABLED (BYO)` txAdmin/server-data provisioning

## Developer Notes

### Run File

- **Executable**: `opt/cfx-server/run.sh`
- **Location**: `<install_dir>/opt/cfx-server/run.sh`
- **Engine**: Custom

### Server Configuration

- **Config file**: usually `server-data/server.cfg` for vanilla deployments, or the
  txAdmin-managed profile under `txData/`
- **Template**: See [server-templates/gtafivemserver/](../server-templates/gtafivemserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
