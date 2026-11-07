# RedM

This guide covers the `redmserver` module in AlphaGSM.

`redmserver` is currently `ENABLED (AUTH)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around the required txAdmin/server-data
provisioning plus Cfx license-key flow, while local runs remain
process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- a Cfx.re server license key
- operator-managed txAdmin or vanilla `server-data` provisioning
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myredmserv create redmserver
```

Run setup:

```bash
alphagsm myredmserv setup
```

`redmserver` is supported in `ENABLED (AUTH)` mode. AlphaGSM can download the
current Linux RedM artifact, but you still need to complete one of the
supported Cfx provisioning flows before the server is actually ready:

- txAdmin first-run provisioning against the downloaded artifact, including
  browser-based account linking, PIN entry, and recipe/profile creation, or
- a pre-staged vanilla `server-data/` tree with a valid `server.cfg`, license
  key, resources, and any other RedM configuration you intend to run

Start it:

```bash
alphagsm myredmserv start
```

Check it:

```bash
alphagsm myredmserv status
```

Stop it:

```bash
alphagsm myredmserv stop
```

## Setup Details

Setup configures:

- the game port (default 30120)
- the install directory
- downloads and extracts the server archive

Suggested txAdmin-oriented flow:

```bash
alphagsm myredmserv create redmserver
alphagsm myredmserv setup -n 30120 /path/to/redmserver
alphagsm myredmserv start
# complete txAdmin provisioning in the browser against the downloaded artifact
```

Suggested vanilla/server-data flow:

```bash
alphagsm myredmserv create redmserver
alphagsm myredmserv setup -n 30120 /path/to/redmserver
# stage your server-data tree with server.cfg and sv_licenseKey
alphagsm myredmserv start
```

## Useful Commands

```bash
alphagsm myredmserv update
alphagsm myredmserv backup
```

## Notes

- Module name: `redmserver`
- Default port: 30120
- Install mode: `ENABLED (AUTH)` txAdmin/server-data provisioning

<!-- alphagsm-server-variables:start -->

## Server variables

After `create redmserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `run.sh`
- **Location**: `<install_dir>/run.sh`
- **Engine**: Custom

### Server Configuration

- **Config file**: usually `server-data/server.cfg` for vanilla deployments, or the
  txAdmin-managed profile under `txData/`
- **Template**: See [server-templates/redmserver/](../server-templates/redmserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
